"""This module handles ALL AMQP protocol logic in INTERSECT. We seek to entirely abstract protocols away from users.

This is a very specific pub-sub model which assumes a single topic exchange.
AMQP topics in INTERSECT generally look like ${ORGANIZATION}.${HIERARCHY}.${SYSTEM}.${SUBSYSTEM}.${SERVICE}.${MESSAGE_TYPE} .
MESSAGE_TYPE refers to INTERSECT domain messages - we do not allow users to determine their own message types directly, and every message has a message type.
SERVICE refers to a specific application.
SYSTEM is generally the level where Auth should occur, and where you should configure access control on the broker itself.
"""

from __future__ import annotations

import functools
import threading
from hashlib import sha384
from typing import TYPE_CHECKING, Callable

import pika
import pika.delivery_mode
import pika.exceptions
import pika.frame

from ...logger import logger
from ...multi_flag_thread_event import MultiFlagThreadEvent
from .broker_client import BrokerClient

if TYPE_CHECKING:
    from pika.channel import Channel
    from pika.frame import Frame
    from pika.spec import Basic, BasicProperties

    from ..topic_handler import TopicHandler


_AMQP_MAX_RETRIES = 10

_PREFETCH_COUNT = 1
"""This determines the maximum amount of messages a single consumer will handle. The consumer must acknowledge the message before it gets another message."""

# Note that we deliberately do NOT want this configurable at runtime. Any two INTERSECT services/clients could potentially exchange messages between one another.
_INTERSECT_MESSAGE_EXCHANGE = 'intersect-messages'
"""All INTERSECT messages get published to one exchange on the broker."""


class ConsumerTagInfo:
    def __init__(self) -> None:
        self.consumer_tag = ''
        self.consumer_tag_event = threading.Event()

    def obtain_consumer_tag(self, consumer_tag: str) -> None:
        self.consumer_tag = consumer_tag
        self.consumer_tag_event.set()

    def consumer_tag_obtained(self) -> bool:
        return self.consumer_tag_event.is_set()

    def wait(self, time: float) -> None:
        self.consumer_tag_event.wait(time)

    def __repr__(self) -> str:
        return f'{self.consumer_tag} -- OBTAINED: {self.consumer_tag_obtained()}'


def _get_queue_name(routing_key: str) -> str:
    """Generate a valid queue name from the routing key.

    We want to always be able to generate the same queue name from the routing key every time,
    so we don't use UUIDs or want the broker to generate a key name.

    We must also keep the length under 128 characters.

    See https://www.rabbitmq.com/docs/queues#names for a complete reference.
    """
    return sha384(routing_key.encode()).hexdigest()


# TODO we should be handling hierarchy parts as a list of strings until they get to the client
# this will be a breaking change, so only add it when ready to break
def _hierarchy_2_amqp(hierarchy: str) -> str:
    """Take the hierarchy string format saved in the Service and map it to the AMQP topic format."""
    return hierarchy.replace('/', '.')


# TODO see above
def _amqp_2_hierarchy(amqp_routing_key: str) -> str:
    """Convert AMQP topic formats to how we store a key in the ControlPlaneManager."""
    return amqp_routing_key.replace('.', '/')


class AMQPClient(BrokerClient):
    """Client for performing broker actions backed by a AMQP broker.

    NOTE: Currently, thread safety has been attempted, but may not be guaranteed

    Attributes:
        id: A string representation of the client's UUID.
        _connection_params: connection information to the AMQP broker (includes credentials)
        _publish_connection: AMQP connection dedicated to publishing messages
        _consume_connection: AMQP connection dedicated to consuming messages
        _topics_to_handlers: Dictionary of string topic names to lists of
            Callables to invoke for messages on that topic.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        topics_to_handlers: Callable[[], dict[str, TopicHandler]],
    ) -> None:
        """The default constructor.

        Args:
            host: String for hostname of AMQP broker
            port: port number of AMQP broker
            username: username credentials for AMQP broker
            password: password credentials for AMQP broker
            topics_to_handlers: callback function which gets the topic to handler map from the channel manager
        """
        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host='/',
            credentials=pika.PlainCredentials(username, password),
            connection_attempts=3,
            # if not specified, this value is obtained by the broker. RabbitMQ sets it to 60s by default
            heartbeat=10,
            blocked_connection_timeout=5.0,
            retry_delay=0.5,
        )

        # The pika connection to the broker
        self._connection: pika.adapters.SelectConnection = None
        self._channel_in: Channel = None
        self._channel_out: Channel = None

        self._thread: threading.Thread | None = None

        # Callback to the topics_to_handler list inside of
        self._topics_to_handlers = topics_to_handlers
        # mapping of topics to callables which can unsubscribe from the topic
        self._topics_to_consumer_tags: dict[str, ConsumerTagInfo] = {}
        self._consumer_tags_to_threads: dict[str, threading.Thread] = {}

        self._should_disconnect = False
        self._connection_retries = 0
        self._unrecoverable = False
        # tracking both channels is the best way to handle continuations
        self._channel_flags = MultiFlagThreadEvent(2)

    def connect(self) -> None:
        """Connect to the defined broker.

        Try to connect to the broker, performing exponential backoff if connection fails.
        """
        self._should_disconnect = False
        self._channel_flags.unset_all()

        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._init_connection, daemon=True)
            self._thread.start()

        while not self._channel_flags.is_set():
            self._channel_flags.wait(1.0)

    def disconnect(self) -> None:
        """Close all connections."""
        self._should_disconnect = True
        for topic, tag_info in self._topics_to_consumer_tags.items():
            self._cancel_consumer_tag(topic, tag_info.consumer_tag)

        # since _should_disconnect was set, _connection.ioloop.stop() will now execute after explicit connection close
        self._connection.close()

        if self._thread:
            # If gracefully shutting down, we should finish up the current job.
            self._thread.join(5 if self.considered_unrecoverable() else None)
            self._thread = None

    def is_connected(self) -> bool:
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        # We are connected to the broker if either the publish or consume connections is open
        return self._connection is not None and (
            not self._connection.is_closed or not self._connection.is_closing
        )

    def considered_unrecoverable(self) -> bool:
        return self._unrecoverable

    def publish(self, topic: str, payload: bytes, persist: bool) -> None:
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string
            payload: The message to publish, as raw bytes.
            persist: True if message should persist until consumers available, False if message should be removed immediately.
        """
        topic = _hierarchy_2_amqp(topic)
        while not self._channel_flags.is_set():
            self._channel_flags.wait(1.0)
        if self._connection and self._connection.is_open:
            self._channel_out.basic_publish(
                exchange=_INTERSECT_MESSAGE_EXCHANGE,
                routing_key=topic,
                body=payload,
                properties=pika.BasicProperties(
                    content_type='text/plain',
                    delivery_mode=pika.delivery_mode.DeliveryMode.Persistent
                    if persist
                    else pika.delivery_mode.DeliveryMode.Transient,
                    # expiration=None if persist else '8640000',
                ),
            )
        else:
            logger.error('Unable to publish message %s on topic %s', payload, topic)

    def subscribe(self, topic: str, persist: bool) -> None:
        """Subscribe to a topic.

        topic: system-of-system hierarchy. In AMQP parlance this gets translated to the routing key.
        persist: If True, we will create an idempotent queue name which should persist
          even on broker or application shutdown. If False, we will allow the server to create a unique
          queue name, and the queue will be destroyed once the associated channel is closed.

        """
        topic = _hierarchy_2_amqp(topic)
        cb = functools.partial(
            self._create_queue, channel=self._channel_in, topic=topic, persist=persist
        )
        self._connection.ioloop.add_callback_threadsafe(cb)

    def unsubscribe(self, topic: str) -> None:
        """Stop consuming from a topic.

        With INTERSECT's AMQP configuration, each queue will only have one consumer.
        Therefore, transient queues will be cleaned up.
        """
        amqp_topic = _hierarchy_2_amqp(topic)
        consumer_tag_info = self._topics_to_consumer_tags.get(amqp_topic, None)
        if consumer_tag_info:
            self._cancel_consumer_tag(amqp_topic, consumer_tag_info.consumer_tag)

    def _cancel_consumer_tag(self, topic: str, consumer_tag: str) -> None:
        if self._channel_in and self._channel_in.is_open:
            cb = functools.partial(
                self._cancel_consumer_tag_cb, topic=topic, consumer_tag=consumer_tag
            )
            self._channel_in.basic_cancel(
                consumer_tag,
                callback=cb,
            )

    def _cancel_consumer_tag_cb(
        self, _frame: pika.frame.Frame, topic: str, consumer_tag: str
    ) -> None:
        try:
            del self._topics_to_consumer_tags[topic]
        except KeyError:
            # shouldn't happen because ControlPlaneManager gatekeeps consecutive remove_subscription_channel() calls
            logger.error(
                'Unable to clean up consumer tag related to topic %s , please inform an INTERSECT-SDK developer if you somehow see this message.',
                topic,
            )
        logger.info('Unsubscribed from %s', topic)
        try:
            thread = self._consumer_tags_to_threads[consumer_tag]
            # kill thread immediately if not recoverable, wait to send last message if we are shutting down gracefully
            thread.join(0 if self.considered_unrecoverable() else None)
            del self._consumer_tags_to_threads[consumer_tag]
            logger.debug('Consumer cancelled')
        except KeyError:
            # This will commonly be encountered, as several topics will often share a single consumer
            pass

    # BEGIN CALLBACKS + THREADSAFE FUNCTIONS #

    def _init_connection(self) -> None:
        """Open the consuming connection and start its io loop.

        NOTE: ANY functions which are not eventually called from this function
        should be called via self._connection.ioloop.add_callback_threadsafe(cb)
        """
        self._connection = None
        self._channel_in = None
        self._channel_out = None

        while not self._should_disconnect and not self.considered_unrecoverable():
            if not self._connection or self._connection.is_closed:
                self._connection = pika.adapters.SelectConnection(
                    parameters=self._connection_params,
                    on_close_callback=self._on_connection_closed,
                    on_open_error_callback=self._on_connection_open_error,
                    on_open_callback=self._on_connection_open,
                )

            # Loops forever until ioloop.stop is called WHEN self._should_disconnect is True
            self._connection.ioloop.start()

    def _on_connection_closed(self, connection: pika.SelectConnection, reason: Exception) -> None:
        """This method is called if the connection to RabbitMQ closes."""
        if self._should_disconnect:
            connection.ioloop.stop()
        else:
            logger.warning('Connection closed, reopening in 5 seconds: %s', reason)
            connection.ioloop.call_later(5, connection.ioloop.stop)
        self._channel_flags.unset_all()
        self._channel_out = None
        self._channel_in = None

    def _on_connection_open_error(
        self, connection: pika.SelectConnection, err: pika.exceptions.AMQPConnectionError
    ) -> None:
        """This gets called if the connection to RabbitMQ can't be established.

        This function usually implies a misconfiguration in the application config.
        """
        self._connection_retries += 1
        logger.error(
            f'On connect error received (probable broker config error), have tried {self._connection_retries} times'
        )
        logger.error(err)
        if self._connection_retries >= _AMQP_MAX_RETRIES:
            # This will allow us to break out of the while loop
            # where we establish the connection, as ioloop.stop
            # will now stop the thread for good
            logger.error('Giving up AMQP reconnection attempt')
            self._should_disconnect = True
            self._unrecoverable = True
            self._channel_flags.set_all()
            connection.ioloop.stop()
        else:
            logger.error('Reopening in 5 seconds')
            connection.ioloop.call_later(5, connection.ioloop.stop)

    def _on_connection_open(self, connection: pika.SelectConnection) -> None:
        logger.info('AMQP connection open')
        self._connection_retries = 0
        self._topics_to_consumer_tags.clear()
        connection.channel(on_open_callback=self._on_input_channel_open)
        connection.channel(on_open_callback=self._on_output_channel_open)

    def _on_channel_closed(
        self,
        channel: Channel,
        exception: pika.exceptions.ChannelClosed,
        channel_num: int,
    ) -> None:
        self._channel_flags.unset_nth_flag(channel_num)
        if self._connection.is_open:
            # This should rarely happen in practice, should only happen if you attempt to do something which violates the protocol.
            logger.error(
                'Closing connection due to closed channel %s, please check the usage of the SDK or your configuration. Exception: %s',
                channel,
                str(exception),
            )
            self._connection.close(reply_code=exception.reply_code, reply_text=exception.reply_text)

    # PRODUCER #
    def _on_output_channel_open(self, channel: Channel) -> None:
        channel_num = 0
        self._channel_out = channel
        cb = functools.partial(self._on_channel_closed, channel_num=channel_num)
        self._channel_out.add_on_close_callback(cb)
        # producer flag should first make sure the exchange exists before publishing
        channel.exchange_declare(
            exchange=_INTERSECT_MESSAGE_EXCHANGE,
            exchange_type='topic',
            durable=True,
            callback=lambda _frame: self._channel_flags.set_nth_flag(channel_num),
        )
        logger.info('AMQP: output channel ready')

    # CONSUMER #
    def _on_input_channel_open(self, channel: Channel) -> None:
        channel_num = 1
        self._channel_in = channel
        # consumer channel flag can be set immediately
        self._channel_flags.set_nth_flag(channel_num)
        cb_1 = functools.partial(self._on_channel_closed, channel_num=channel_num)
        self._channel_in.add_on_close_callback(cb_1)
        cb_2 = functools.partial(self._on_exchange_declareok, channel=channel)
        channel.exchange_declare(
            exchange=_INTERSECT_MESSAGE_EXCHANGE, exchange_type='topic', durable=True, callback=cb_2
        )

    def _on_exchange_declareok(self, _unused_frame: Frame, channel: Channel) -> None:
        """Create a queue on the broker (called from AMQP).

        After verifying that the exchange exists, we can now proceed to execute
        "initial subscriptions".

        Args:
            _unused_frame: response from declaring the exchange on the broker (irrelevant).
            channel: The Channel being instantiated.
        """
        for topic, topic_handler in self._topics_to_handlers().items():
            amqp_topic = _hierarchy_2_amqp(topic)
            cb = functools.partial(
                self._create_queue,
                channel=channel,
                topic=amqp_topic,
                persist=topic_handler.topic_persist,
            )
            self._connection.ioloop.add_callback_threadsafe(cb)

    def _create_queue(self, channel: Channel, topic: str, persist: bool) -> None:
        """Create a queue on the broker.

        This can be called directly from the AMQP Client if the subscribed connection already has a Channel it's listening to.

        Args:
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
            persist: boolean value to determine how we manage the queue.
              If True, this queue will persist forever, even on application or broker shutdown, and we need a persistent name.
              If False, we will generate a temporary queue using the broker's naming scheme.
        """
        cb = functools.partial(
            self._on_queue_declareok, channel=channel, topic=topic, persist=persist
        )
        channel.queue_declare(
            queue=_get_queue_name(topic)
            if persist
            else '',  # if we're transient, let the broker generate a name for us
            durable=persist,
            exclusive=not persist,  # transient queues can be exclusive
            callback=cb,
        )

    def _on_queue_declareok(
        self, frame: Frame, channel: Channel, topic: str, persist: bool
    ) -> None:
        """Begins listening on the given queue.

        Used as a listener on queue declaration.

        Args:
            frame: Response from the queue declare we sent to the AMQP broker. We get the queue name from this.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
            persist: Whether or not our queue should persist on either broker or application shutdown.
        """
        queue_name = frame.method.queue
        cb = functools.partial(
            self._on_queue_bindok,
            channel=channel,
            topic=topic,
            queue_name=queue_name,
            persist=persist,
        )
        channel.queue_bind(
            queue=queue_name,
            exchange=_INTERSECT_MESSAGE_EXCHANGE,
            routing_key=topic,
            callback=cb,
        )

    def _on_queue_bindok(
        self,
        _unused_frame: Frame,
        channel: Channel,
        topic: str,
        queue_name: str,
        persist: bool,
    ) -> None:
        """Sets up basic QOS on the current channel.

        Args:
            _unused_frame: AMQP response from binding to the queue. Ignored.
            channel: The Channel being instantiated.
            topic: Name of the topic on the broker.
            queue_name: The name of the queue on the AMQP broker.
            persist: Whether or not our queue should persist on either broker or application shutdown.
        """
        cb = functools.partial(
            self._on_basic_qos_set,
            channel=channel,
            topic=topic,
            queue_name=queue_name,
            persist=persist,
        )
        channel.basic_qos(prefetch_count=_PREFETCH_COUNT, callback=cb)

    def _on_basic_qos_set(
        self,
        _unused_frame: Frame,
        channel: Channel,
        topic: str,
        queue_name: str,
        persist: bool,
    ) -> None:
        """Consumes a message from the given channel.

        Used as a listener on queue binding.

        Args:
            _unused_frame: AMQP response from binding to the queue. Ignored.
            channel: The Channel being instantiated.
            topic: Name of the topic on the broker.
            queue_name: The name of the queue on the AMQP broker.
            persist: Whether or not our queue should persist on either broker or application shutdown.
        """
        cb = functools.partial(self._on_consume_ok, topic=topic)
        message_cb = functools.partial(self._consume_message, persist=persist)
        info = ConsumerTagInfo()
        self._topics_to_consumer_tags[topic] = info
        consumer_tag = channel.basic_consume(
            queue=queue_name,
            auto_ack=not persist,  # persistent messages should be manually acked and we have no reason to NACK a message for now
            on_message_callback=message_cb,
            callback=cb,
        )
        info.obtain_consumer_tag(consumer_tag)

    def _on_consume_ok(self, _unused_frame: Frame, topic: str) -> None:
        """Sets the consume subscription ready event.

        Used as a listener on consuming an initial message on a channel.

        Args:
            _unused_frame: AMQP response from successfully beginning consumption. Ignored.
            topic: Name of the topic on the broker.
        """
        logger.info('ready to start consuming to %s', topic)

    def _consume_message(
        self,
        channel: Channel,
        basic_deliver: Basic.Deliver,
        _properties: BasicProperties,
        body: bytes,
        persist: bool,
    ) -> None:
        """Handles incoming messages and acknowledges them ONLY after code executes on the domain side.

        Looks up all handlers for the topic and delegates message handling to them.
        The handlers comprise the Service/Client logic, which includes all domain science logic.

        Args:
            channel: The AMQP channel the message was received on. Used to manually acknowledge messages.
            basic_deliver: Contains internal AMQP delivery information - i.e. the routing key.
            _properties: Object from the AMQP call. Ignored.
            body: the AMQP message to be handled.
            persist: Whether or not our queue should persist on either broker or application shutdown.
        """
        # if we got a message when we shouldn't, quickly try to requeue it
        if self.considered_unrecoverable() or self._should_disconnect:
            logger.warning(
                "WARNING: A message for topic %s has been received when it shouldn't, attempting requeue"
            )
            channel.basic_reject(basic_deliver.delivery_tag)
            return

        tth_key = _amqp_2_hierarchy(basic_deliver.routing_key)
        topic_handler = self._topics_to_handlers().get(tth_key)
        if topic_handler:
            consumer_tag_info = self._topics_to_consumer_tags.get(basic_deliver.routing_key)
            if not consumer_tag_info:
                logger.error(
                    'Could not fetch consumer tag for topic %s, please inform an INTERSECT-SDK developer that you saw this message',
                    tth_key,
                )
                return
            while not consumer_tag_info.consumer_tag_obtained():
                consumer_tag_info.wait(1.0)
            thrd = threading.Thread(
                target=self._consume_message_subthread,
                args=(channel, topic_handler.callbacks, body, basic_deliver.delivery_tag, persist),
            )
            self._consumer_tags_to_threads[consumer_tag_info.consumer_tag] = thrd
            thrd.start()
        elif persist:
            # we somehow got a message that we don't want, discard it
            channel.basic_ack(basic_deliver.delivery_tag)

    def _consume_message_subthread(
        self,
        channel: Channel,
        callbacks: set[Callable[[bytes], None]],
        body: bytes,
        delivery_tag: int,
        persist: bool,
    ) -> None:
        """This is a subthread which executes the consumer code without blocking the IO loop. Without using a subthread, the AMQP heartbeat checker will be blocked."""
        for cb in callbacks:
            cb(body)
        # With persistent messages, we only acknowledge the message AFTER we are done processing
        # (this removes the message from the broker queue)
        # this allows us to retry a message if the broker OR this application goes down
        # We currently never NACK or reject a message because in INTERSECT, applications currently never "share" a queue.
        if persist:
            channel.basic_ack(delivery_tag)

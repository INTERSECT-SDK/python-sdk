from __future__ import annotations

import functools
import threading
import uuid
from typing import TYPE_CHECKING, Callable

import pika
from retrying import retry

from .broker_client import BrokerClient

if TYPE_CHECKING:
    from collections import defaultdict

    from pika.channel import Channel
    from pika.frame import Frame
    from pika.spec import Basic, BasicProperties


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
        topics_to_handlers: Callable[[], defaultdict[str, set[Callable[[bytes], None]]]],
        uid: str | None = None,
    ) -> None:
        """The default constructor.

        Args:
            host: String for hostname of AMQP broker
            port: port number of AMQP broker
            username: username credentials for AMQP broker
            password: password credentials for AMQP broker
            topics_to_handlers: callback function which gets the topic to handler map from the channel manager
            uid: String for the client's UUID.
        """
        self.uid = uid if uid else str(uuid.uuid4())

        self._connection_params = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host='/',
            credentials=pika.PlainCredentials(username, password),
            blocked_connection_timeout=1,
        )

        # The pika connection to the broker
        self._publish_connection: pika.adapters.BlockingConnection = None
        self._consume_connection: pika.adapters.SelectConnection = None
        self._consume_connection_ready_event = threading.Event()
        self._consume_subscription_ready_event = threading.Event()

        # Callback to the topics_to_handler list inside of
        self._topics_to_handlers = topics_to_handlers
        # mapping of topics to callables which can unsubscribe from the topic
        self._topics_to_channel_cancel_callbacks: dict[str, Callable[[], None]] = {}
        self._consumer_thread = None

    @retry(
        stop_max_attempt_number=5,
        wait_exponential_multiplier=1000,
        wait_exponential_max=60000,
    )
    def connect(self) -> None:
        """Connect to the defined broker.

        Try to connect to the broker, performing exponential backoff if connection fails.
        """
        # need deamon=True otherwise if tests fails it hangs trying to acquire lock
        self.thread = threading.Thread(target=self._start_consuming, daemon=True)
        self.thread.start()
        self._publish_connection = pika.adapters.BlockingConnection(self._connection_params)
        self._consume_connection_ready_event.wait(timeout=5)

    def disconnect(self) -> None:
        """Close all connections.

        Close both the public and consume connections and stop the consuming thread.
        """
        self._publish_connection.close()
        self._publish_connection = None
        self._consume_connection.ioloop.add_callback_threadsafe(self._close_consume_connection)
        # as soon as connection is closed, the ioloop.stop will be
        # called which in turn will terminate the consuming thread
        self.thread.join(5)
        self._consume_connection = None

    def is_connected(self) -> bool:
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        # We are connected to the broker if either the publish or consume connections is open
        return (self._publish_connection is not None and self._publish_connection.is_open) or (
            self._consume_connection is not None and self._consume_connection.is_open
        )

    def publish(self, topic: str, payload: bytes) -> None:
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string
            payload: The message to publish, as raw bytes.
        """
        channel = self._publish_connection.channel()
        channel.exchange_declare(topic, exchange_type='fanout', durable=True)
        # this will send the message to topic exchange and distribute to all
        # queues that subscribed to it
        channel.basic_publish(
            exchange=topic,
            routing_key=topic,
            body=payload,
            properties=pika.BasicProperties(content_type='text/plain'),
        )
        channel.close()

    def subscribe(self, topic: str) -> None:
        self._consume_subscription_ready_event.clear()
        self._subscribe_to_queue(topic)
        self._consume_subscription_ready_event.wait()

    def unsubscribe(self, topic: str) -> None:
        old_channel = self._topics_to_channel_cancel_callbacks.get(topic, None)
        if old_channel:
            old_channel()
            del self._topics_to_channel_cancel_callbacks[topic]

    def _start_consuming(self) -> None:
        """Start consuming messages from broker.

        Open the consuming connection and start its io loop.
        """
        self._consume_connection = pika.adapters.SelectConnection(
            parameters=self._connection_params,
            on_close_callback=(
                lambda _connection, _exception: self._consume_connection.ioloop.stop()
            ),
            on_open_callback=lambda _connection: self._consume_connection_ready_event.set(),
        )

        self._consume_connection.ioloop.start()

    def _subscribe_to_queue(self, topic: str) -> None:
        """Start consuming from the given topic.

        Declares the correct exchange and queue on the broker if needed, then starts
        consuming messages on that queue.

        Args:
            topic: Name of the topic on the broker to subscribe to as a string.
        """
        # in consumer thread: open channel-> declare queue (need that if we starte
        # consuming  before message is published (no queue yet)) -> start consuming
        cb = functools.partial(self._open_channel, topic=topic)
        self._consume_connection.ioloop.add_callback_threadsafe(cb)

    def _open_channel(self, topic: str) -> None:
        """Open a channel for the given topic.

        Args:
            topic: The topic to open a channel for as a string.
        """
        cb = functools.partial(self._on_channel_open, topic=topic)
        self._consume_connection.channel(on_open_callback=cb)

    def _on_channel_open(self, channel: Channel, topic: str) -> None:
        """Create an exchange on the broker.

        Used as a listener on channel open.

        Args:
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_exchange_declareok, channel=channel, topic=topic)
        channel.exchange_declare(exchange=topic, exchange_type='fanout', durable=True, callback=cb)

    def _on_exchange_declareok(self, _unused_frame: Frame, channel: Channel, topic: str) -> None:
        """Create a queue on the broker.

        Used as a listener on exchange declaration.

        Args:
            _unused_frame: Object from pika. Ignored.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_queue_declareok, channel=channel, topic=topic)
        channel.queue_declare(queue=topic + '.' + self.uid, durable=True, callback=cb)

    def _on_queue_declareok(self, _unused_frame: Frame, channel: Channel, topic: str) -> None:
        """Begins listening on the given queue.

        Used as a listener on queue declaration.

        Args:
            _unused_frame: Object from pika. Ignored.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_queue_bindok, channel=channel, topic=topic)
        channel.queue_bind(topic + '.' + self.uid, topic, routing_key=topic, callback=cb)

    def _on_queue_bindok(self, _unused_frame: Frame, channel: Channel, topic: str) -> None:
        """Consumes a message from the given channel.

        Used as a listener on queue binding.

        Args:
            _unused_frame: Object from pika. Ignored.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_consume_ok)
        consumer_tag = channel.basic_consume(
            queue=topic + '.' + self.uid,
            auto_ack=True,
            on_message_callback=self._consume_message,
            callback=cb,
        )
        self._topics_to_channel_cancel_callbacks[topic] = lambda: channel.basic_cancel(consumer_tag)

    def _on_consume_ok(self, _unused_frame: Frame) -> None:
        """Sets the consume subscription ready even.

        Used as a listener on consuming an initial message on a channel.

        Args:
            _unused_frame: Object from pika. Ignored.
            topic: The string name for the Channel on the broker.
        """
        self._consume_subscription_ready_event.set()

    def _consume_message(
        self,
        _unused_channel: Channel,
        basic_deliver: Basic.Deliver,
        _properties: BasicProperties,
        body: bytes,
    ) -> None:
        """Handles incoming messages.

        Looks up all handlers for the topic and delegates message handling to them.

        Args:
            _unused_channel: The Pika channel the message was received on. Ignored
            basic_deliver: Contains internal Pika delivery information - i.e. the routing key.
            _properties: Object from the Pika call. Ignored.
            body: the pika message to be handled.
        """
        for handler in self._topics_to_handlers().get(basic_deliver.routing_key, []):
            handler(body)

    def _close_consume_connection(self) -> None:
        """Closes the consume connection.

        Used as a listener on the connection loop to safely shutdown.
        """
        self._consume_connection.close()
        self._topics_to_channel_cancel_callbacks.clear()

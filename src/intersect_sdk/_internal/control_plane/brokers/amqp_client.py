"""This module handles ALL AMQP protocol logic in INTERSECT. We seek to entirely abstract protocols away from users.

This is a very specific pub-sub model which assumes a single topic exchange.
AMQP topics in INTERSECT generally look like ${ORGANIZATION}.${HIERARCHY}.${SYSTEM}.${SUBSYSTEM}.${SERVICE}.${MESSAGE_TYPE} .
MESSAGE_TYPE refers to INTERSECT domain messages - we do not allow users to determine their own message types directly, and every message has a message type.
SERVICE refers to a specific application.
SYSTEM is generally the level where Auth should occur, and where you should configure access control on the broker itself.
"""

from __future__ import annotations

import functools
import random
import threading
import time
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

    from ....config.shared import BrokerConfig
    from ..topic_handler import TopicHandler


_AMQP_MAX_RETRIES = 10


class ClusterConnectionParameters:
    """Configuration for an AMQP cluster.

    Attributes:
        brokers: List of broker configurations for AMQP cluster nodes
        username: AMQP broker username
        password: AMQP broker password
        connection_attempts: Number of connection attempts per node
        connection_retry_delay: Delay between connection attempts in seconds
    """

    def __init__(
        self,
        brokers: list[BrokerConfig],
        username: str,
        password: str,
        connection_attempts: int = 3,
        connection_retry_delay: float = 2.0,
    ) -> None:
        """Initialize cluster connection parameters.

        Args:
            brokers: List of broker configurations for AMQP cluster nodes
            username: AMQP broker username
            password: AMQP broker password
            connection_attempts: Number of connection attempts per node
            connection_retry_delay: Delay between connection attempts in seconds
        """
        self.brokers = brokers
        self.username = username
        self.password = password
        self.connection_attempts = connection_attempts
        self.connection_retry_delay = connection_retry_delay

    def get_random_node(self) -> BrokerConfig:
        """Get a random node from the cluster.

        Returns:
            A BrokerConfig randomly selected from the available cluster nodes
        """
        index = random.randint(0, len(self.brokers) - 1)  # noqa: S311
        return self.brokers[index]

    def get_next_node(self, previous_index: int | None = None) -> tuple[int, BrokerConfig]:
        """Get the next node in a round-robin fashion.

        Args:
            previous_index: Index of the previously used node

        Returns:
            A tuple containing (index, BrokerConfig) of the next node to try
        """
        if previous_index is None or previous_index >= len(self.brokers) - 1:
            next_index = 0
        else:
            next_index = previous_index + 1

        return next_index, self.brokers[next_index]


# Note that we deliberately do NOT want this configurable at runtime. Any two INTERSECT services/clients could potentially exchange messages between one another.
_INTERSECT_MESSAGE_EXCHANGE = 'intersect-messages'
"""All INTERSECT messages get published to one exchange on the broker."""


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


def _check_broker_connectivity(host: str, port: int, timeout: int = 2.0) -> bool:
    """Check if we can connect to a broker host:port.

    Returns True if reachable, False otherwise.
    """
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0  # noqa: TRY300 annoyingly, lint complains about this if I put it in an if/else also. It's circular in suggestions.
    except socket.gaierror:
        # Handle name resolution errors specially
        return False
    return True


class AMQPClient(BrokerClient):
    """Client for performing broker actions backed by a AMQP broker.

    NOTE: Currently, thread safety has been attempted, but may not be guaranteed

    Attributes:
        username: Username for broker authentication.
        password: Password for broker authentication.
        _publish_connection: AMQP connection dedicated to publishing messages
        _consume_connection: AMQP connection dedicated to consuming messages
        _topics_to_handlers: Dictionary of string topic names to lists of
            Callables to invoke for messages on that topic.
    """

    def __init__(
        self,
        topics_to_handlers: Callable[[], dict[str, TopicHandler]],
        cluster_params: ClusterConnectionParameters,
    ) -> None:
        """The default constructor.

        Args:
            username: username credentials for AMQP broker
            password: password credentials for AMQP broker
            topics_to_handlers: callback function which gets the topic to handler map from the channel manager
            cluster_params: Optional cluster configuration parameters. If provided, brokers/username/password are ignored.
        """
        self._cluster_params: ClusterConnectionParameters = cluster_params
        self._current_broker_index: int = None

        # The pika connection to the broker
        self._connection: pika.adapters.SelectConnection = None
        self._channel_in: Channel = None
        self._channel_out: Channel = None

        self._thread: threading.Thread | None = None
        self._node_reconnect_thread: threading.Thread | None = None

        # Callback to the topics_to_handler list inside of
        self._topics_to_handlers = topics_to_handlers
        # mapping of topics to callables which can unsubscribe from the topic
        self._topics_to_consumer_tags: dict[str, str] = {}

        self._should_disconnect = False
        self._connection_retries = 0
        self._unrecoverable = False
        # tracking both channels is the best way to handle continuations
        self._channel_flags = MultiFlagThreadEvent(2)
        self._cluster_connection_attempts = 0

    def connect(self) -> None:
        """Connect to the defined broker.

        Try to connect to the broker, performing exponential backoff if connection fails.
        """
        self._should_disconnect = False
        self._unrecoverable = False
        self._connection_retries = 0
        self._channel_flags.unset_all()

        self._current_broker_index = 0
        logger.info(f'Starting with broker index {self._current_broker_index} (first broker)')

        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._init_connection, daemon=True, name='amqp_init_connection'
            )
            self._thread.start()

        timeout = 30.0
        start_time = time.time()
        while not self._channel_flags.is_set():
            if time.time() - start_time > timeout:
                logger.error(f'Timeout waiting for AMQP connection after {timeout} seconds')
                break
            self._channel_flags.wait(1.0)

    def disconnect(self) -> None:
        """Close all connections."""
        self._should_disconnect = True
        for topic, tag in self._topics_to_consumer_tags.items():
            self._cancel_consumer_tag(topic, tag)

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
        # We need to check both the connection and at least one channel
        is_conn_ok = self._connection is not None and not self._connection.is_closed
        has_channel = (self._channel_in is not None and self._channel_in.is_open) or (
            self._channel_out is not None and self._channel_out.is_open
        )

        # Only consider ourselves connected if we have both a connection and at least one channel
        logger.debug(f'Connection status: conn={is_conn_ok}, channel={has_channel}')
        return is_conn_ok and has_channel

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
        consumer_tag = self._topics_to_consumer_tags.get(amqp_topic, None)
        if consumer_tag:
            self._cancel_consumer_tag(amqp_topic, consumer_tag)

    def _cancel_consumer_tag(self, topic: str, consumer_tag: str) -> None:
        if self._channel_in and self._channel_in.is_open:
            cb = functools.partial(self._cancel_consumer_tag_cb, topic=topic)
            self._channel_in.basic_cancel(
                consumer_tag,
                callback=cb,
            )

    def _cancel_consumer_tag_cb(self, _frame: pika.frame.Frame, topic: str) -> None:
        try:
            del self._topics_to_consumer_tags[topic]
        except KeyError:
            # shouldn't happen because ControlPlaneManager gatekeeps consecutive remove_subscription_channel() calls
            pass
        logger.info('Unsubscribed from %s', topic)

    # BEGIN CALLBACKS + THREADSAFE FUNCTIONS #

    def _init_connection(self) -> None:
        """Open the consuming connection and start its io loop."""
        # Start with a clean state
        self._connection = None
        self._channel_in = None
        self._channel_out = None

        # Main connection loop - run until shutdown or all brokers fail
        while not self._should_disconnect and not self._unrecoverable:
            try:
                # Initialize broker index if needed
                if self._current_broker_index is None:
                    self._current_broker_index = 0

                # Get current broker info
                broker = self._cluster_params.brokers[self._current_broker_index]
                logger.warning(
                    f'====== TRYING BROKER {self._current_broker_index}: {broker.host}:{broker.port} ======'
                )

                # Check server availability with TCP connection test first
                try:
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1.0)

                    # Try to connect directly with TCP
                    result = sock.connect_ex((broker.host, broker.port))
                    sock.close()

                    # If we can't connect at TCP level, try next broker right away
                    if result != 0:
                        logger.warning(
                            f'✗ TCP connectivity test failed for {broker.host}:{broker.port} (error: {result})'
                        )

                        # Move to next broker if we have multiple
                        if len(self._cluster_params.brokers) > 1:
                            self._current_broker_index = (self._current_broker_index + 1) % len(
                                self._cluster_params.brokers
                            )
                            logger.warning(
                                f'Switching to next broker (index {self._current_broker_index})'
                            )
                            time.sleep(0.5)  # Brief delay to avoid hammering servers
                            continue
                        # No other brokers to try, pause longer before retry
                        logger.warning(
                            'No alternative brokers available, retrying same one in a moment...'
                        )
                        time.sleep(2.0)
                        continue
                except Exception as e:  # noqa: BLE001 I think I can clean this up later but for now catching it all.
                    # Handle DNS resolution or other socket-related errors gracefully
                    logger.warning(
                        f'✗ Socket connection error for {broker.host}:{broker.port}: {e!s}'
                    )

                    # If we already have an active connection to another broker, don't disrupt it
                    if self.is_connected():
                        logger.info(
                            f'Already connected to another broker, will retry {broker.host} later'
                        )
                        time.sleep(5.0)  # Longer delay when already connected
                        continue

                    # Otherwise, try the next broker
                    if len(self._cluster_params.brokers) > 1:
                        self._current_broker_index = (self._current_broker_index + 1) % len(
                            self._cluster_params.brokers
                        )
                        logger.warning(
                            f'Socket error, switching to broker {self._current_broker_index}'
                        )
                        time.sleep(0.5)
                        continue
                    logger.warning('Socket error with only broker, waiting to retry...')
                    time.sleep(2.0)
                    continue

                # TCP connection successful, now try AMQP connection
                logger.info(
                    f'✓ TCP connection succeeded for {broker.host}:{broker.port}, now trying AMQP connection'
                )

                self._connection = pika.adapters.SelectConnection(
                    parameters=pika.ConnectionParameters(
                        host=broker.host,
                        port=broker.port,
                        virtual_host='/',
                        credentials=pika.PlainCredentials(
                            self._cluster_params.username, self._cluster_params.password
                        ),
                        connection_attempts=1,  # Only try once
                        heartbeat=10,
                        retry_delay=0.5,
                    ),
                    on_close_callback=self._on_connection_closed,
                    on_open_error_callback=self._on_connection_open_error,
                    on_open_callback=self._on_connection_open,
                )

                # Start IO loop - blocks until connection closes
                self._connection.ioloop.start()

                # If we get here, the IO loop has stopped - check why
                if self._should_disconnect:
                    logger.info('Connection loop exited due to shutdown request')
                    break

                # If not shutting down, we must have had a connection failure
                logger.warning('Connection IO loop exited, will retry...')

                # Brief pause before trying again
                time.sleep(1.0)

            except Exception as e:  # noqa: BLE001 I think I can clean this up later but for now catching it all.
                # Log any unexpected errors
                logger.error(f'⚠️ Unexpected error in connection attempt: {e!s}')
                self._connection = None  # Ensure connection is cleared

                # Increment broker index to try next one
                if len(self._cluster_params.brokers) > 1:
                    self._current_broker_index = (self._current_broker_index + 1) % len(
                        self._cluster_params.brokers
                    )

                # Brief pause before retry
                time.sleep(1.0)

    def _get_current_connection_params(self) -> pika.ConnectionParameters:
        """Get connection parameters for the current broker index."""
        broker = self._cluster_params.brokers[self._current_broker_index]

        # Log current broker info
        logger.info(f'Setting up connection parameters for broker: {broker.host}:{broker.port}')

        # IMPORTANT: Force connection_attempts=1 to ensure we don't retry using pika's
        # internal retry mechanism, which can get stuck when DNS issues occur
        # We handle retries ourselves at the AMQP client level
        return pika.ConnectionParameters(
            host=broker.host,
            port=broker.port,
            virtual_host='/',
            credentials=pika.PlainCredentials(
                self._cluster_params.username, self._cluster_params.password
            ),
            connection_attempts=1,  # CRITICAL: Only try once per broker
            heartbeat=10,  # Faster heartbeat for quicker failure detection
            blocked_connection_timeout=5.0,  # Detect blocked connections faster
            retry_delay=0.5,  # Minimal delay between retries
        )

    def _on_connection_closed(self, connection: pika.SelectConnection, reason: Exception) -> None:
        """This method is called if the connection to RabbitMQ closes."""
        logger.warning(
            f'Connection closed on broker index {self._current_broker_index}, reason: {reason}'
        )

        # Store the broker that failed for later reference
        failed_broker_index = self._current_broker_index
        failed_broker = self._cluster_params.brokers[failed_broker_index]

        # Clean up connection state for this specific connection only
        # We might still have other connections active, so don't clear everything
        if connection == self._connection:
            self._channel_flags.unset_all()
            self._channel_out = None
            self._channel_in = None
            self._connection = None

        # Stop the IO loop if requested
        if self._should_disconnect:
            connection.ioloop.stop()
            return

        # We need to switch to the next broker if we have multiple
        if len(self._cluster_params.brokers) > 1:
            # Increment broker index to try the next one
            self._current_broker_index = (self._current_broker_index + 1) % len(
                self._cluster_params.brokers
            )
            next_broker = self._cluster_params.brokers[self._current_broker_index]
            logger.info(
                f'Connection closed on {failed_broker.host}, SWITCHING to BROKER {next_broker.host}'
            )

            # Try a quick connectivity test to the next broker
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((next_broker.host, next_broker.port))
            sock.close()

            if result == 0:
                logger.info(
                    f'Successfully verified TCP connectivity to {next_broker.host}:{next_broker.port}'
                )
            else:
                logger.warning(
                    f'TCP connection test to {next_broker.host}:{next_broker.port} failed (error: {result})'
                )

                # If this is our second broker and we know the first is down, continue with this one
                # Otherwise, switch back if we still have a connection to the original broker
                if self.is_connected() and self._current_broker_index != failed_broker_index:
                    logger.info('Already connected to a working broker, keeping that connection')
                    self._current_broker_index = failed_broker_index

        # Always stop the IO loop - this is what triggers reconnection
        connection.ioloop.stop()

    def _on_connection_open_error(
        self, connection: pika.SelectConnection, err: pika.exceptions.AMQPConnectionError
    ) -> None:
        """This gets called if the connection to RabbitMQ can't be established."""
        current_broker = self._cluster_params.brokers[self._current_broker_index]
        logger.error(f'CONNECTION ERROR to broker {current_broker.host}: {err!s}')

        # Increment retry count
        self._connection_retries += 1

        # Print error details to help debugging
        connection_params = self._get_current_connection_params()
        logger.info(f'Connection parameters: {connection_params}')

        # Always try next node in cluster
        if len(self._cluster_params.brokers) > 1:
            # Move to the next broker
            old_index = self._current_broker_index
            self._current_broker_index = (self._current_broker_index + 1) % len(
                self._cluster_params.brokers
            )
            next_broker = self._cluster_params.brokers[self._current_broker_index]

            # Reset connection retries when switching to a new broker
            self._connection_retries = 0

            # Check if we're already connected before trying to switch
            if self.is_connected():
                logger.info(
                    'Already connected to a working broker, staying with current connection'
                )
                # If we're connected, don't try to switch brokers
                return

            logger.warning(
                f'SWITCHING from broker {old_index} to {self._current_broker_index} ({next_broker.host})'
            )

            # Try to immediately connect to verify the next broker
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((next_broker.host, next_broker.port))
            sock.close()

            if result == 0:
                logger.info(
                    f'✓ Successfully verified TCP connectivity to {next_broker.host}:{next_broker.port}'
                )
            else:
                logger.warning(
                    f'✗ TCP connection test to {next_broker.host}:{next_broker.port} failed (error: {result})'
                )
        elif self._connection_retries >= _AMQP_MAX_RETRIES:
            # Give up if we've tried too many times
            logger.error(f'Giving up AMQP connection after {self._connection_retries} retries')
            self._channel_flags.set_all()
            self._unrecoverable = True

        # Clean up and force reconnection
        self._connection = None
        connection.ioloop.stop()

    def _on_connection_open(self, connection: pika.SelectConnection) -> None:
        """Called when connection to RabbitMQ is established."""
        current_broker = self._cluster_params.brokers[self._current_broker_index]
        logger.info(f'AMQP connection open to broker {current_broker.host}:{current_broker.port}')

        # Reset retries and clear state on successful connection
        self._connection_retries = 0
        self._topics_to_consumer_tags.clear()

        # Check connectivity to both brokers for diagnosis
        for i, broker in enumerate(self._cluster_params.brokers):
            can_connect = _check_broker_connectivity(broker.host, broker.port)
            logger.info(f'Broker {i} ({broker.host}:{broker.port}) reachable: {can_connect}')
        # Open the channels
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
        # Resubscribe to all topics to ensure queues and bindings are re-established
        for topic, _ in self._topics_to_handlers().items():
            logger.info(f'Resubscribing to topic: {topic}')
            self.subscribe(topic, True)

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
        # Resubscribe to all topics to ensure queues and bindings are re-established
        for topic, _ in self._topics_to_handlers().items():
            logger.info(f'Resubscribing to topic: {topic}')
            self.subscribe(topic, True)

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
        consumer_tag = channel.basic_consume(
            queue=queue_name,
            auto_ack=not persist,  # persistent messages should be manually acked and we have no reason to NACK a message for now
            on_message_callback=message_cb,
            callback=cb,
        )
        self._topics_to_consumer_tags[topic] = consumer_tag

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
        tth_key = _amqp_2_hierarchy(basic_deliver.routing_key)
        topic_handler = self._topics_to_handlers().get(tth_key)
        if topic_handler:
            for cb in topic_handler.callbacks:
                cb(body)
        # With persistent messages, we only acknowledge the message AFTER we are done processing
        # (this removes the message from the broker queue)
        # this allows us to retry a message if the broker OR this application goes down
        # We currently never NACK or reject a message because in INTERSECT, applications currently never "share" a queue.
        if persist:
            channel.basic_ack(basic_deliver.delivery_tag)

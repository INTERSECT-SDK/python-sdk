import functools
import threading
import uuid

# third party
import pika
from retrying import retry

# project
from .broker_client import BrokerClient


class AMQPClient(BrokerClient):
    """
    Client for performing broker actions backed by a AMQP broker.

    Attributes:
        id: A string representation of the client's UUID.
        topics_to_handlers: Dictionary of string topic names to lists of
            Callables to invoke for messages on that topic.
    """

    def __init__(self, id=None):
        """The default constructor.

        Args:
            id: String for the client's UUID.
        """
        BrokerClient.__init__(self)

        if id:
            self.id = id
        else:
            self.id = str(uuid.uuid1())
        # The pika connection to the broker
        self._publish_connection = None
        self._consume_connection = None
        self._consume_connection_ready_event = threading.Event()
        self._consume_subscription_ready_event = threading.Event()

        # Map of topic names to the ordered list of MessageHandlers to handle
        # messages for a topic
        self.topics_to_handlers = {}
        self.lock = threading.Lock()
        self._connection_params = None
        self._consumer_thread = None

    def _set_channel(self, new_channel):
        """Setter for the channel.

        Args:
            new_channel: The new channel
        """
        self._channel = new_channel

    def consume_message(self, _unused_channel, basic_deliver, properties, body):
        """Handles incoming messages.

        Looks up all handlers for the topic and delegates message handling to them.

        Args:
            client: The paho client the message was received on. Ignored.
            userdata: Object from the paho call. Ignored.
            message: the paho message to be handled.
        """
        # Pass the payload to each handler for this topic
        self.lock.acquire()
        for handler in self.topics_to_handlers[basic_deliver.routing_key]:
            # If the handler returns false, do not pass the message to
            # subsequent handlers in the list
            if not handler.on_receive(basic_deliver.routing_key, body):
                # Handler signalled to halt message handling
                break
        self.lock.release()

    def _on_open(self, connection):
        """Sets the consume connection's ready event.

        Used as a listener on the channel to set the channel state on connection opening.

        Args:
            connection: SelectConnection sent from pika. Ignored.
        """
        self._consume_connection_ready_event.set()

    def _close_consume_connection(self):
        """Closes the consume connection.

        Used as a listener on the connection loop to safely shutdown.
        """
        self._consume_connection.close()

    def _on_close(self, connection, exception):
        """Stop the consume connection's io loop.

        Used as a listener to stop the io loop when the connection is closed.

        Args:
            connection: SelectConnection from pika. Ignored.
            exception: Exception from pika. Ignored.
        """
        self._consume_connection.ioloop.stop()

    def close_connections(self):
        """Close all connections.

        Close both the public and consume connections and stop the consuming thread.
        """
        self._publish_connection.close()
        self._consume_connection.ioloop.add_callback_threadsafe(self._close_consume_connection)
        # as soon as connection is closed, the ioloop.stop will be
        # called which in turn will terminate the consuming thread
        self.thread.join(5)

    def _start_consuming(self):
        """Start consuming messages from broker.

        Open the consuming connection and start its io loop.
        """
        self._consume_connection = pika.adapters.select_connection.SelectConnection(
            self._connection_params,
            on_close_callback=self._on_close,
            on_open_callback=self._on_open,
        )

        self._consume_connection.ioloop.start()

    @retry(stop_max_attempt_number=5, wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def connect(self, host, port, username, password):
        """Connect to the defined broker.

        Try to connect to the broker, performing exponential backoff if connection fails.

        Args:
            host: Broker's hostname as a string
            port: Broker's port as a string
            username: Username
            password: Password
        """

        credentials = pika.PlainCredentials(username, password)
        self._connection_params = pika.ConnectionParameters(host, port, "/", credentials)
        self._connection_params.blocked_connection_timeout = 1
        # need deamon=True otherwise if tests fails it hangs trying to acquire lock
        self.thread = threading.Thread(target=self._start_consuming, daemon=True)
        self.thread.start()
        self._publish_connection = pika.adapters.blocking_connection.BlockingConnection(
            self._connection_params
        )
        self._consume_connection_ready_event.wait(timeout=5)

    def publish(self, topic, payload):
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string
            payload: The message to publish as a string.
        """

        channel = self._publish_connection.channel()
        channel.exchange_declare(topic, exchange_type="fanout", durable=True)
        # this will send the message to topic exchange and distribute to all
        # queues that subscribed to it
        channel.basic_publish(
            exchange=topic,
            routing_key=topic,
            body=payload,
            properties=pika.BasicProperties(content_type="text/plain"),
        )
        channel.close()

    def _open_channel(self, topic):
        """Open a channel for the given topic.

        Args:
            topic: The topic to open a channel for as a string.
        """
        cb = functools.partial(self._on_channel_open, topic=topic)
        self._consume_connection.channel(on_open_callback=cb)

    def _on_channel_open(self, channel, topic):
        """Create an exchange on the broker.

        Used as a listener on channel open.

        Args:
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_exchange_declareok, channel=channel, topic=topic)
        channel.exchange_declare(exchange=topic, exchange_type="fanout", durable=True, callback=cb)

    def _on_exchange_declareok(self, _unused_frame, channel, topic):
        """Create a queue on the broker

        Used as a listener on exchange declaration.

        Args:
            _unused_frame: Object from pika. Ignored.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_queue_declareok, channel=channel, topic=topic)
        channel.queue_declare(queue=topic + "." + self.id, durable=True, callback=cb)

    def _on_queue_declareok(self, _unused_frame, channel, topic):
        """Begins listening on the given queue.

        Used as a listener on queue declaration.

        Args:
            _unused_frame: Object from pika. Ignored.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_queue_bindok, channel=channel, topic=topic)
        channel.queue_bind(topic + "." + self.id, topic, routing_key=topic, callback=cb)

    def _on_queue_bindok(self, _unused_frame, channel, topic):
        """Consumes a message from the given channel.

        Used as a listener on queue binding.

        Args:
            _unused_frame: Object from pika. Ignored.
            channel: The Channel being instantiated.
            topic: The string name for the Channel on the broker.
        """
        cb = functools.partial(self._on_consume_ok, topic=topic)
        channel.basic_consume(
            queue=topic + "." + self.id,
            auto_ack=True,
            on_message_callback=self.consume_message,
            callback=cb,
        )

    def _on_consume_ok(self, _unused_frame, topic):
        """Sets the consume subscription ready even.

        Used as a listener on consuming an initial message on a channel.

        Args:
            _unused_frame: Object from pika. Ignored.
            topic: The string name for the Channel on the broker.
        """
        self._consume_subscription_ready_event.set()

    def _subscribe_to_queue(self, topic):
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

    def subscribe(self, topics, handler):
        """Subscribe to one or more topics over the pre-existing connection (via connect()).

        Handlers will be invoked in the order in which they were given to subscribe().

        Args:
            topics: List of strings of topics to subscribe to.
            handler: Callable to be invoked  on the incoming messages from the subscribed
                topics.
        """

        # For each topic, add the handler
        for topic in topics:
            # If there are no handlers for this topic, make a new list
            if topic not in self.topics_to_handlers:
                self.lock.acquire()
                self.topics_to_handlers[topic] = []
                self.lock.release()
                self._consume_subscription_ready_event.clear()
                self._subscribe_to_queue(topic)
                self._consume_subscription_ready_event.wait()

            # Append the handler to the list of handlers
            self.lock.acquire()
            self.topics_to_handlers[topic].append(handler)
            self.lock.release()

    def is_connected(self):
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """

        # We are connected to the broker if either the publish or consume connections is open
        return (self._publish_connection is not None and self._publish_connection.is_open) or (
            self._consume_connection is not None and self._consume_connection.is_open
        )

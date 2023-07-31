# third-party
import paho.mqtt.client as paho_client
from retrying import retry

# project
from .broker_client import BrokerClient


class MQTTClient(BrokerClient):
    """Client for performing broker actions backed by a MQTT broker.

    Attributes:
        uid: String defining this client's unique ID in the broker
        topics_to_handlers: Dictionary of string topic names to lists of
            Callables to invoke for messages on that topic.
    """

    def __init__(self, uid):
        """The default constructor.

        Args:
            uid: A string representing the unique id to identify the client.
        """
        BrokerClient.__init__(self, uid)

        # Unique id for the MQTT broker to associate this client with
        self.uid = uid

        # The paho client which is connected to the broker
        self._connection = None

        # Whether the connection is currently active
        self._connected = False

        # Map of topic names to the ordered list of MessageHandlers to handle
        # messages for a topic
        self.topics_to_handlers = {}

    def consume_message(self, client, userdata, message):
        """Handles incoming messages.

        Looks up all handlers for the topic and delegates message handling to them.

        Args:
            client: The paho client the message was received on. Ignored.
            userdata: Object from the paho call. Ignored.
            message: the paho message to be handled.
        """

        # Pass the payload to each handler for this topic
        for handler in self.topics_to_handlers[message.topic]:
            # If the handler returns false, do not pass the message to
            # subsequent handlers in the list
            if not handler.on_receive(message.topic, message.payload):
                # Something failed?
                break

    @retry(stop_max_attempt_number=5, wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def connect(self, host, port, username, password):
        """Connect to the defined broker.

        Args:
            host: Broker's hostname as a string.
            port: Broker's port as a string.
            username: Broker's username as a string.
            password: Broker's password as a string.
        """

        # Create a client to connect to RabbitMQ
        self._connection = paho_client.Client(client_id=self.uid, clean_session=False)
        self._connection.on_connect = self._set_connection_status
        self._connection.on_disconnect = self._handle_disconnect
        self._connection.username_pw_set(username=username, password=password)
        self._connection.connect(host, port, 60)

        # Add function to consume messages
        self._connection.on_message = self.consume_message

    def is_connected(self):
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """

        return self._connected

    def _handle_disconnect(self, client, userdata, rc):
        """Handle a disconnection from the MQTT server.

        Args:
            client: The Paho client.
            userdata: MQTT user data.
            rc: MQTT return code as an integer.
        """

        self._connected = False

    def publish(self, topic, payload):
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish as a string.
        """

        self._connection.publish(topic, payload, qos=2)

    def _set_connection_status(self, client, userdata, flags, rc):
        """Set the connection status in response to the result of a Paho connection attempt.

        Args:
            client: The Paho MQTT client.
            userdata: The MQTT userdata.
            flags: List of MQTT connection flags.
            rc: The MQTT return code as an int.
        """

        # Return code 0 means connection was successful
        if rc == 0:
            self._connected = True
        else:
            self._connected = False

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
                self.topics_to_handlers[topic] = []

            # Append the handler to the list of handlers
            self.topics_to_handlers[topic].append(handler)

            # Subscribe the client to the topic
            self._connection.subscribe([(topic, 2)])
            # self._connection.subscribe(channel, callback)

        # Start consuming messages
        self._connection.loop_start()

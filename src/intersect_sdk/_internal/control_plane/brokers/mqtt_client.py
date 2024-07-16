from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING, Any, Callable

import paho.mqtt.client as paho_client
from retrying import retry

from .broker_client import BrokerClient

if TYPE_CHECKING:
    from ..topic_handler import TopicHandler


class MQTTClient(BrokerClient):
    """Client for performing broker actions backed by a MQTT broker.

    Note that this class may not be thread safe, see https://github.com/eclipse/paho.mqtt.python/issues/358#issuecomment-1880819505

    Attributes:
        uid: String defining this client's unique ID in the broker
        host: hostname of MQTT broker
        port: port of MQTT broker
        _connection: Paho Client used to interact with the broker
        _connected: current state of whether or not we're connected to the broker (boolean)
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
        uid: str | None = None,
    ) -> None:
        """The default constructor.

        Args:
            host: String for hostname of MQTT broker
            port: port number of MQTT broker
            username: username credentials for MQTT broker
            password: password credentials for MQTT broker
            topics_to_handlers: callback function which gets the topic to handler map from the channel manager
            uid: A string representing the unique id to identify the client.
        """
        # Unique id for the MQTT broker to associate this client with
        self.uid = uid if uid else str(uuid.uuid4())
        self.host = host
        self.port = port

        # Create a client to connect to RabbitMQ
        # TODO clean_session param is ONLY for MQTT v3 here
        self._connection = paho_client.Client(client_id=self.uid, clean_session=False)
        self._connection.username_pw_set(username=username, password=password)

        # Whether the connection is currently active
        self._connected = False
        self._should_disconnect = False
        self._topics_to_handlers = topics_to_handlers

        # MQTT callback functions
        self._connection.on_connect = self._handle_connect
        self._connection.on_disconnect = self._handle_disconnect
        self._connection.on_message = self._on_message

    @retry(stop_max_attempt_number=5, wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def connect(self) -> None:
        """Connect to the defined broker."""
        # Create a client to connect to RabbitMQ
        # TODO MQTT v5 implementations should set clean_start to NEVER here
        self._connection.connect(self.host, self.port, 60)
        self._connection.loop_start()
        while not self.is_connected():
            time.sleep(0.1)

    def disconnect(self) -> None:
        """Disconnect from the broker."""
        self._should_disconnect = True
        self._connection.disconnect()
        self._connection.loop_stop()

    def is_connected(self) -> bool:
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        return self._connected

    def publish(self, topic: str, payload: bytes, persist: bool) -> None:
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish, as raw bytes.
            persist: Determine if the message should live until queue consumers or available (True), or
              if it should be removed immediatedly (False)
        """
        # NOTE: RabbitMQ only works with QOS of 1 and 0, and seems to convert QOS2 to QOS1
        self._connection.publish(topic, payload, qos=2 if persist else 0)

    def subscribe(self, topic: str, persist: bool) -> None:
        """Subscribe to a topic over the pre-existing connection (via connect()).

        Args:
            topic: Topic to subscribe to.
            persist: Determine if the associated message queue of the topic is long-lived (True) or not (False)
        """
        # NOTE: RabbitMQ only works with QOS of 1 and 0, and seems to convert QOS2 to QOS1
        self._connection.subscribe(topic, qos=2 if persist else 0)

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic over the pre-existing connection.

        Args:
          topic: Topic to unsubscribe from.
        """
        self._connection.unsubscribe(topic)

    def _on_message(
        self, _client: paho_client.Client, _userdata: Any, message: paho_client.MQTTMessage
    ) -> None:
        """Handle a message from the MQTT server.

        Args:
          _client: the Paho client
          _userdata: MQTT user data
          message: MQTT message
        """
        topic_handler = self._topics_to_handlers().get(message.topic)
        if topic_handler:
            for cb in topic_handler.callbacks:
                cb(message.payload)

    def _handle_disconnect(self, client: paho_client.Client, _userdata: Any, _rc: int) -> None:
        """Handle a disconnection from the MQTT server.

        Args:
            client: The Paho client.
            _userdata: MQTT user data.
            rc: MQTT return code as an integer.
        """
        self._connected = False
        if not self._should_disconnect:
            client.reconnect()

    def _handle_connect(
        self, _client: paho_client.Client, _userdata: Any, _flags: dict[str, Any], rc: int
    ) -> None:
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
            self._should_disconnect = False
            for topic, topic_handler in self._topics_to_handlers().items():
                self.subscribe(topic, topic_handler.topic_persist)
        else:
            self._connected = False

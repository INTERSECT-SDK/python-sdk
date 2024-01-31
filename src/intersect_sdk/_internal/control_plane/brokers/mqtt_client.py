from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Callable

import paho.mqtt.client as paho_client
from retrying import retry

from .broker_client import BrokerClient

if TYPE_CHECKING:
    from collections import defaultdict


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
        topics_to_handlers: Callable[[], defaultdict[str, set[Callable[[bytes], None]]]],
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
        self._topics_to_handlers = topics_to_handlers

        # MQTT callback functions
        self._connection.on_connect = self._set_connection_status
        self._connection.on_disconnect = self._handle_disconnect
        self._connection.on_message = self._on_message

    @retry(stop_max_attempt_number=5, wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def connect(self) -> None:
        """Connect to the defined broker."""
        # Create a client to connect to RabbitMQ
        # TODO MQTT v5 implementations should set clean_start to NEVER here
        self._connection.connect(self.host, self.port, 60)
        self._connection.loop_start()

    def disconnect(self) -> None:
        """Disconnect from the broker."""
        self._connection.disconnect()
        self._connection.loop_stop()

    def is_connected(self) -> bool:
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        return self._connected

    def publish(self, topic: str, payload: bytes) -> None:
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish, as raw bytes.
        """
        self._connection.publish(topic, payload, qos=2)

    def subscribe(self, topic: str) -> None:
        """Subscribe to a topic over the pre-existing connection (via connect()).

        Args:
            topic: Topic to subscribe to.
        """
        self._connection.subscribe(topic, qos=2)

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
        for handler in self._topics_to_handlers().get(message.topic, []):
            handler(message.payload)

    def _handle_disconnect(self, _client: paho_client.Client, _userdata: Any, _rc: int) -> None:
        """Handle a disconnection from the MQTT server.

        Args:
            _client: The Paho client.
            _userdata: MQTT user data.
            rc: MQTT return code as an integer.
        """
        self._connected = False

    def _set_connection_status(
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
        else:
            self._connected = False

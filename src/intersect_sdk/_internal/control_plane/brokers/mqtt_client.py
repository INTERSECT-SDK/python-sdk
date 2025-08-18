from __future__ import annotations

import threading
import uuid
from typing import TYPE_CHECKING, Any

import paho.mqtt.client as paho_client
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from retrying import retry

from ...logger import logger
from .broker_client import BrokerClient

if TYPE_CHECKING:
    from collections.abc import Callable

    from paho.mqtt.client import DisconnectFlags
    from paho.mqtt.reasoncodes import ReasonCode

    from ..topic_handler import TopicHandler


_MQTT_MAX_RETRIES = 10


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
        self._connection = paho_client.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            protocol=paho_client.MQTTv5,
            client_id=self.uid,
        )
        self._connection.username_pw_set(username=username, password=password)

        # Whether the connection is currently active
        self._connected = False
        self._should_disconnect = False
        self._unrecoverable = False
        self._connection_retries = 0
        self._connected_flag = threading.Event()

        # ConnectionManager callable state
        self._topics_to_handlers = topics_to_handlers

        # MQTT v3.1.1 automatically downgrades a QOS which is too high (good), but MQTT v5 will terminate the connection (bad)
        # see https://github.com/rabbitmq/rabbitmq-server/discussions/11842
        self._max_supported_qos = 2

        # MQTT callback functions
        self._connection.on_connect = self._handle_connect
        self._connection.on_disconnect = self._handle_disconnect
        self._connection.on_message = self._on_message

    @retry(stop_max_attempt_number=5, wait_exponential_multiplier=1000, wait_exponential_max=60000)
    def connect(self) -> None:
        """Connect to the defined broker."""
        # Create a client to connect to RabbitMQ
        self._should_disconnect = False
        self._connected_flag.clear()
        self._connection.connect(
            self.host,
            self.port,
            60,
            clean_start=False,
        )
        self._connection.loop_start()
        while not self.is_connected() and not self._connected_flag.is_set():
            self._connected_flag.wait(1.0)

    def disconnect(self) -> None:
        """Disconnect from the broker."""
        self._should_disconnect = True
        if self._connection:
            self._connection.disconnect()
            self._connection.loop_stop()

    def is_connected(self) -> bool:
        """Check if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        return self._connected

    def considered_unrecoverable(self) -> bool:
        return self._unrecoverable

    def publish(
        self, topic: str, payload: bytes, content_type: str, headers: dict[str, str], persist: bool
    ) -> None:
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish, as raw bytes.
            content_type: The content type of the message (if the data plane used is the control plane itself), or the value to be retrieved from the data plane (if the message handler is MINIO/etc.)
            headers: UTF-8 dictionary which can help parse information about the message
            persist: Determine if the message should live until queue consumers or available (True), or
              if it should be removed immediately (False)
        """
        props = Properties(PacketTypes.PUBLISH)  # type: ignore[no-untyped-call]
        props.ContentType = content_type
        props.UserProperty = list(headers.items())
        self._connection.publish(
            topic, payload, qos=self._max_supported_qos if persist else 0, properties=props
        )

    def subscribe(self, topic: str, persist: bool) -> None:
        """Subscribe to a topic over the pre-existing connection (via connect()).

        Args:
            topic: Topic to subscribe to.
            persist: Determine if the associated message queue of the topic is long-lived (True) or not (False)
        """
        # NOTE: RabbitMQ only works with QOS of 1 and 0, and seems to convert QOS2 to QOS1
        self._connection.subscribe(topic, qos=2 if persist else 0, properties=None)

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic over the pre-existing connection.

        Args:
          topic: Topic to unsubscribe from.
        """
        self._connection.unsubscribe(topic)

    def _on_message(
        self,
        client: paho_client.Client,  # noqa: ARG002
        userdata: Any,  # noqa: ARG002
        message: paho_client.MQTTMessage,
    ) -> None:
        """Handle a message from the MQTT server.

        Args:
          client: the Paho client
          userdata: MQTT user data
          message: MQTT message
        """
        topic_handler = self._topics_to_handlers().get(message.topic)
        # Note that if we return prior to the callback, there will be no reply message
        if not topic_handler:
            logger.warning('Incompatible message topic %s, rejecting message', message.topic)
            return
        try:
            content_type = message.properties.ContentType  # type: ignore[union-attr]
            headers = dict(message.properties.UserProperty)  # type: ignore[union-attr]
        except AttributeError as e:
            logger.warning(
                'Missing mandatory property %s in received message. The message will be rejected',
                e.name,
            )
            return
        except ValueError:
            logger.warning(
                'Headers in received message are in improper format. The message will be rejected'
            )
            return
        for cb in topic_handler.callbacks:
            cb(message.payload, content_type, headers)

    def _handle_disconnect(
        self,
        client: paho_client.Client,
        userdata: Any,
        flags: DisconnectFlags,
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        """Handle a disconnection from the MQTT server.

        This callback usually implies a temporary connection fault, so we'll try to handle it.

        Args:
            client: The Paho client.
            userdata: MQTT user data.
            flags: List of MQTT connection flags.
            reason_code: MQTT return code.
            properties: MQTT user properties.
        """
        logger.debug(
            'mqtt disconnected log - uid=%s reason_code=%s flags=%s userdata=%s properties=%s',
            self.uid,
            reason_code,
            flags,
            userdata,
            properties,
        )
        self._connected = False
        if not self._should_disconnect:
            client.reconnect()

    def _handle_connect(
        self,
        client: paho_client.Client,  # noqa: ARG002
        userdata: Any,
        flags: dict[str, Any],
        reason_code: ReasonCode,
        properties: Properties | None,
    ) -> None:
        """Set the connection status in response to the result of a Paho connection attempt.

        If rc is 0, connection was successful - if not,
        this usually implies a misconfiguration in the application config.

        Args:
            client: The Paho MQTT client.
            userdata: The MQTT userdata.
            flags: List of MQTT connection flags.
            reason_code: The MQTT return code.
            properties: MQTT user properties
        """
        if str(reason_code) == 'Success':
            logger.debug(
                'MQTT connected log - reason-code=%s properties=%s userdata=%s flags=%s',
                reason_code,
                properties,
                userdata,
                flags,
            )
            self._connected = True
            self._connection_retries = 0
            self._should_disconnect = False

            # mimic "automatic QoS downgrade" of MQTTv3 for MQTTv5
            if properties and hasattr(properties, 'MaximumQoS'):
                logger.info('MQTT: Maximum supported QoS is %s', properties.MaximumQoS)
                self._max_supported_qos = properties.MaximumQoS

            self._connected_flag.set()
            for topic, topic_handler in self._topics_to_handlers().items():
                self.subscribe(topic, topic_handler.topic_persist)
        else:
            # This will generally suggest a misconfiguration
            self._connected = False
            self._connection_retries += 1
            logger.error('Bad connection (reason: %s)', reason_code)
            logger.error(
                'On connect error received (probable broker config error), have tried %s times',
                self._connection_retries,
            )
            logger.error('Connection error userdata: %s', userdata)
            logger.error('Connection error flags: %s', flags)
            if self._connection_retries >= _MQTT_MAX_RETRIES:
                logger.error('Giving up MQTT reconnection attempt')
                self._connected_flag.set()
                self._unrecoverable = True

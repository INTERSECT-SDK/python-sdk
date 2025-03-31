from __future__ import annotations

import random
import threading
import time
import uuid
from typing import TYPE_CHECKING, Any, Callable

import paho.mqtt.client as paho_client

from ...logger import logger
from .broker_client import BrokerClient

if TYPE_CHECKING:
    from ....config.shared import BrokerConfig
    from ..topic_handler import TopicHandler

_MQTT_MAX_RETRIES = 10
_MQTT_RECONNECT_DELAY = 5  # Seconds to wait before reconnection attempts


class ClusterConnectionParameters:
    """Configuration for an MQTT cluster.

    Attributes:
        brokers: List of broker configurations for MQTT cluster nodes
        username: MQTT broker username
        password: MQTT broker password
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
            brokers: List of broker configurations for MQTT cluster nodes
            username: MQTT broker username
            password: MQTT broker password
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


class MQTTClient(BrokerClient):
    """Client for performing broker actions backed by a MQTT broker.

    Note that this class may not be thread safe, see https://github.com/eclipse/paho.mqtt.python/issues/358#issuecomment-1880819505

    Attributes:
        uid: String defining this client's unique ID in the broker
        _cluster_params: Connection information to the MQTT broker cluster
        _current_node_index: Index of the current node being used
        _connection: Paho Client used to interact with the broker
        _connected: current state of whether or not we're connected to the broker (boolean)
        _topics_to_handlers: Dictionary of string topic names to lists of
            Callables to invoke for messages on that topic.
    """

    def __init__(
        self,
        cluster_params: ClusterConnectionParameters,
        topics_to_handlers: Callable[[], dict[str, TopicHandler]] | None = None,
        uid: str | None = None,
    ) -> None:
        """The default constructor.

        Args:
            username: username credentials for MQTT broker (ignored if cluster_params is provided)
            password: password credentials for MQTT broker (ignored if cluster_params is provided)
            topics_to_handlers: callback function which gets the topic to handler map from the channel manager
            cluster_params: Optional cluster configuration parameters. If provided, host/port/username/password are ignored.
            uid: A string representing the unique id to identify the client.
        """
        # Unique id for the MQTT broker to associate this client with
        self.uid = uid if uid else str(uuid.uuid4())

        # If cluster_params is provided, use it. Otherwise, create a single-node configuration.
        self._cluster_params: ClusterConnectionParameters = cluster_params
        self._current_node_index: int | None = None
        self._connection: paho_client.Client | None = None
        self._initialize_connection()

        # Whether the connection is currently active
        self._connected = False
        self._should_disconnect = False
        self._unrecoverable = False
        self._connection_retries = 0
        self._connected_flag = threading.Event()
        self._cluster_connection_attempts = 0
        self._node_reconnect_thread: threading.Thread | None = None

        # ConnectionManager callable state
        self._topics_to_handlers = topics_to_handlers

    def _initialize_connection(self) -> None:
        """Initialize the MQTT connection with the current broker."""
        if self._connection is not None:
            self._connection.disconnect()
            self._connection.loop_stop()

        # Select a node to connect to if we don't have one
        if self._current_node_index is None:
            self._current_node_index, broker = self._cluster_params.get_next_node()
        else:
            # Use the current node
            broker = self._cluster_params.brokers[self._current_node_index]

        logger.info(f'Initializing MQTT connection to {broker.host}:{broker.port}')

        # Create a client to connect to RabbitMQ
        # TODO clean_session param is ONLY for MQTT v3 here
        self._connection = paho_client.Client(client_id=self.uid, clean_session=False)
        self._connection.username_pw_set(
            username=self._cluster_params.username, password=self._cluster_params.password
        )

        # MQTT callback functions
        self._connection.on_connect = self._handle_connect
        self._connection.on_disconnect = self._handle_disconnect
        self._connection.on_message = self._on_message

    def connect(self) -> None:
        """Connect to the defined broker."""
        self._should_disconnect = False
        self._connected_flag.clear()
        self._try_connect_to_current_node()

    def _try_connect_to_current_node(self) -> None:
        """Attempt to connect to the currently selected node."""
        if self._current_node_index is None:
            self._current_node_index = self._cluster_params.get_next_node()[0]
        host = self._cluster_params.brokers[self._current_node_index].host
        port = self._cluster_params.brokers[self._current_node_index].port

        logger.info(f'Attempting to connect to MQTT node: {host}:{port}')

        # Reset connection if needed
        if not hasattr(self._connection, 'is_connected'):
            self._initialize_connection()

        # Connect and start the loop
        self._connection.connect(host, port, 60)
        self._connection.loop_start()

        # Wait for connection to be established
        timeout = 10  # shorter timeout for faster failover
        start_time = time.time()
        while not self.is_connected() and not self._connected_flag.is_set():
            if time.time() - start_time > timeout:
                break
            self._connected_flag.wait(1.0)

        if self.is_connected() and not self._connected_flag.is_set():
            logger.error(f'Error connecting to MQTT node {host}:{port}')
            self._connection_retries += 1

            # Try next node if we have multiple nodes
            if len(self._cluster_params.brokers) > 1 and not self._should_disconnect:
                logger.info(
                    f'Will try next node in cluster (retries so far: {self._connection_retries})'
                )
                self._try_next_node()
            elif self._connection_retries >= _MQTT_MAX_RETRIES:
                # Only give up after we've tried all nodes multiple times
                total_attempts = _MQTT_MAX_RETRIES * len(self._cluster_params.brokers)
                if self._connection_retries >= total_attempts:
                    logger.error(
                        f'Giving up MQTT reconnection attempt after {self._connection_retries} attempts across all nodes'
                    )
                    self._connected_flag.set()
                    self._unrecoverable = True
                else:
                    # If we're not yet at total attempts but we're out of nodes,
                    # start over with the first node
                    logger.info('Cycling back to first node in cluster')
                    self._current_node_index = None
                    self._try_next_node()

    def _try_next_node(self) -> None:
        """Attempt to connect to the next node in the cluster."""
        if self._node_reconnect_thread and self._node_reconnect_thread.is_alive():
            logger.info('Already attempting to connect to another node')
            return

        # Create a new thread to handle the node switch
        self._node_reconnect_thread = threading.Thread(
            target=self._switch_to_next_node, daemon=True, name='mqtt_node_reconnect'
        )
        self._node_reconnect_thread.start()

    def _switch_to_next_node(self) -> None:
        """Switch to the next node in the cluster and attempt to connect."""
        if self._should_disconnect:
            return

        # Get the next node
        prev_index = self._current_node_index
        self._current_node_index, broker = self._cluster_params.get_next_node(
            self._current_node_index
        )

        logger.info(
            f'Switching from node {prev_index} to node {self._current_node_index} ({broker.host}:{broker.port})'
        )

        # Clean up the old connection
        if self._connection:
            self._connection.disconnect()
            self._connection.loop_stop()

        # Quick failover - don't wait too long
        time.sleep(1.0)

        # Initialize a fresh connection with the new node
        self._initialize_connection()

        # Try to connect to the new node
        logger.info(f'Attempting connection to alternative node: {broker.host}:{broker.port}')
        self._try_connect_to_current_node()

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

    def publish(self, topic: str, payload: bytes, persist: bool) -> None:
        """Publish the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish, as raw bytes.
            persist: Determine if the message should live until queue consumers or available (True), or
              if it should be removed immediately (False)
        """
        # NOTE: RabbitMQ only works with QOS of 1 and 0, and seems to convert QOS2 to QOS1
        if self._connection and self.is_connected():
            try:
                logger.debug(f'Publishing message to topic: {topic}')
                result = self._connection.publish(topic, payload, qos=2 if persist else 0)

                # Check if the publish was successful (rc=0 means success)
                if result.rc != 0:
                    logger.error(f'Failed to publish message (rc={result.rc}): {result}')

                    # If we fail to publish due to connection issues, try reconnecting
                    if not self._should_disconnect:
                        self._connected = False
                        self._try_next_node()
                        # Try publishing again after reconnection
                        if self.is_connected():
                            logger.info('Retrying publish after reconnection')
                            self._connection.publish(topic, payload, qos=2 if persist else 0)
            except Exception as e:  # noqa: BLE001
                logger.error(f'Error publishing message to topic {topic}: {e}')
                # If we encounter an exception, the connection might be bad
                if not self._should_disconnect:
                    self._connected = False
                    self._try_next_node()
        else:
            logger.error('Cannot publish message: not connected to MQTT broker')

            # If we're not connected but should be, try reconnecting
            if not self._should_disconnect:
                logger.info('Attempting reconnection before publishing')
                if self._current_node_index is None:
                    self._current_node_index = 0
                self._try_connect_to_current_node()

                # Try again after reconnection
                if self.is_connected():
                    logger.info('Publishing after reconnection')
                    self._connection.publish(topic, payload, qos=2 if persist else 0)

    def subscribe(self, topic: str, persist: bool) -> None:
        """Subscribe to a topic over the pre-existing connection (via connect()).

        Args:
            topic: Topic to subscribe to.
            persist: Determine if the associated message queue of the topic is long-lived (True) or not (False)
        """
        # NOTE: RabbitMQ only works with QOS of 1 and 0, and seems to convert QOS2 to QOS1
        if self._connection and self.is_connected():
            try:
                logger.info(f'Subscribing to topic: {topic}')
                self._connection.subscribe(topic, qos=2 if persist else 0)
            except Exception as e:  # noqa: BLE001
                logger.error(f'Error subscribing to topic {topic}: {e}')
                # If we fail to subscribe, mark the connection as bad and try to reconnect
                if not self._should_disconnect:
                    self._connected = False
                    self._try_next_node()

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic over the pre-existing connection.

        Args:
          topic: Topic to unsubscribe from.
        """
        if self._connection and self.is_connected():
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

    def _handle_disconnect(self, client: paho_client.Client, _userdata: Any, rc: int) -> None:
        """Handle a disconnection from the MQTT server.

        This callback usually implies a temporary connection fault, so we'll try to handle it.

        Args:
            client: The Paho client.
            _userdata: MQTT user data.
            rc: MQTT return code as an integer.
        """
        # Mark as disconnected
        self._connected = False
        logger.warning(f'MQTT disconnected with code {rc}')

        # If this was an unexpected disconnect, try to reconnect
        if not self._should_disconnect:
            logger.info('Attempting to reconnect to MQTT broker')

            # If we have multiple nodes in the cluster, try the next one
            if len(self._cluster_params.brokers) > 1:
                # Wait a moment to prevent rapid reconnection attempts
                time.sleep(1.0)
                self._try_next_node()
                # Return here since _try_next_node will handle the reconnection
                return
            # With a single node, just try to reconnect to the same node
            try:
                # Don't immediately reconnect - wait a bit to avoid rapid reconnects
                time.sleep(1.0)
                logger.info('Attempting to reconnect to the same MQTT node')
                client.reconnect()
            except Exception as e:  # noqa: BLE001
                logger.error(f'Failed to reconnect to MQTT broker: {e!s}')
                self._connection_retries += 1

                # If we've tried too many times, give up
                if self._connection_retries >= _MQTT_MAX_RETRIES:
                    logger.error('Giving up MQTT reconnection attempt')
                    self._connected_flag.set()
                    self._unrecoverable = True

    def _handle_connect(
        self, client: paho_client.Client, userdata: Any, flags: dict[str, Any], rc: int
    ) -> None:
        """Set the connection status in response to the result of a Paho connection attempt.

        If rc is 0, connection was successful - if not,
        this usually implies a misconfiguration in the application config.

        Args:
            client: The Paho MQTT client.
            userdata: The MQTT userdata.
            flags: List of MQTT connection flags.
            rc: The MQTT return code as an int.
        """
        # Return code 0 means connection was successful
        if rc == 0:
            host = self._cluster_params.brokers[self._current_node_index].host
            port = self._cluster_params.brokers[self._current_node_index].port
            logger.info(f'Successfully connected to MQTT node {host}:{port}')

            self._connected = True
            self._connection_retries = 0
            self._should_disconnect = False
            self._connected_flag.set()

            # Make sure the client is valid and loop is running
            if not hasattr(client, 'is_connected') or client != self._connection:
                logger.warning('Client mismatch in connect callback - recreating connection')
                self._initialize_connection()
                client = self._connection
                client.connect(host, port, 60)
                client.loop_start()

            # Delay slightly before subscribing to ensure connection is fully established
            time.sleep(0.5)

            # Resubscribe to all topics
            logger.info('Resubscribing to topics after connection established')
            topics = self._topics_to_handlers()
            if topics:
                logger.info(f'Resubscribing to {len(topics)} topics')
                for topic, topic_handler in topics.items():
                    logger.info(f'Resubscribing to topic: {topic}')
                    client.subscribe(topic, qos=2 if topic_handler.topic_persist else 0)
            else:
                logger.warning('No topics to resubscribe to!')
        else:
            # This will generally suggest a misconfiguration
            self._connected = False
            self._connection_retries += 1

            host = self._cluster_params.brokers[self._current_node_index].host
            port = self._cluster_params.brokers[self._current_node_index].port

            logger.error(
                f'MQTT connect error (rc={rc}) to {host}:{port}, attempt {self._connection_retries}'
            )
            logger.error(f'Connection error userdata: {userdata}')
            logger.error(f'Connection error flags: {flags}')

            # If we've tried all nodes multiple times, give up
            cluster_max_retries = _MQTT_MAX_RETRIES * len(self._cluster_params.brokers)
            if self._connection_retries >= cluster_max_retries:
                logger.error('Giving up MQTT reconnection attempt after trying all nodes')
                self._connected_flag.set()
                self._unrecoverable = True
            elif len(self._cluster_params.brokers) > 1:
                # Try the next node
                self._try_next_node()

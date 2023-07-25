import json
from typing import Optional

import urllib3

from ..brokers import broker_client
from ..messages import JsonHandler
from ..messages.handlers.serialization_handler import SerializationHandler
from .channel import Channel
from .exceptions import IntersectInvalidBrokerException


class Client:
    """Base client class. Applications should import this and use connect to
    connect to remote brokers and then subscribe to/consume messages from
    channels.

    Attributes:
        broker_client: A BrokerClient to handle the broker connection.
    """

    def __init__(self):
        """The default constructor."""
        self.broker_client = None
        self._broker_endpoint = "intersect-broker"
        self._valid_broker_backends = [
            "rabbitmq-mqtt",
            "rabbitmq-amqp",
        ]

    def _create_broker_client(self, backend_name: str) -> broker_client.BrokerClient:
        """Create a BrokerClient of the appropriate type for the requested backend.

        Args:
            backend_name: A string representing the subclass of BrokerClient to
                create. Valid values are "rabbitmq-mqtt" and "rabbitmq-amqp".
        Returns:
            A BrokerClient of a subclass corresponding to backend_name.
        """

        if backend_name == "rabbitmq-mqtt":
            from ..brokers import mqtt_client

            return mqtt_client.MQTTClient()

        if backend_name == "rabbitmq-amqp":
            try:
                from ..brokers import amqp_client

                return amqp_client.AMQPClient()
            except ImportError:
                raise IntersectInvalidBrokerException(
                    f"Using broker backend {backend_name}, but AMQP dependencies were not installed. Install intersect with the 'amqp' optional dependency to use this backend."
                )

        raise IntersectInvalidBrokerException(
            (
                f"Unknown broker backend: {backend_name}. "
                f"Broker options: {self._valid_broker_backends}"
            )
        )

    def _discover_broker(self, address: str):
        """Get the metadata for a broker from the discovery service.

        Args:
            address: A string containing the address for the discovery service.
        Returns:
            Three strings. The first is the name of the broker type (as used in
            _create_broker_client()), the second is the broker's address, and
            the third is the broker's port number.
        """
        try:
            http = urllib3.PoolManager()
            r = http.request("GET", address + "/v0.1/" + self._broker_endpoint)
            broker_info = json.loads(r.data.decode("utf-8"))
            endpoint = broker_info["endpoint"]
            backend_name = broker_info["backendName"]
            address, port = endpoint.split(":", 1)
            return backend_name, address, port
        except Exception as e:
            raise Exception("cannot discover broker service") from e

    def connect(self, connection: tuple, username, password):
        """Connect to a broker.

        This call will update the internal state of the
        client with new broker information to back channels.

        Args:
            connection: A tuple with connection information, the first two of
                which are address and port.
            username: A string for the broker username.
            password: A string for the broker password.

        Raises:
            IntersectInvalidBrokerException: if invalid broker backend was chosen, or chosen broker backend cannot import necessary modules
        """
        address, port, *others = connection
        use_discovery_service = False
        if others:
            use_discovery_service = others[0]

        backend_name = "rabbitmq-mqtt"
        if use_discovery_service:
            backend_name, address, port = self._discover_broker(address)

        self.broker_client = self._create_broker_client(backend_name)

        self.broker_client.connect(address, port, username, password)

    def channel(self, name: str, serializer: Optional[SerializationHandler] = None):
        """Creates an interface to a broker's channel.

        See class Channel.

        Args:
            name: String name of the channel being connected to
            serializer: An IntersectSerializer responsible for taking the bytes
                received from the broker in the new Channel and turning it into
                a Message object.
        Returns:
            A new Channel with the given channel name and serializer.
        """
        return Channel(
            name,
            self.broker_client,
            serializer=(serializer if serializer is not None else JsonHandler()),
        )

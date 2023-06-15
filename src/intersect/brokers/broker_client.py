from abc import ABC, abstractmethod

from .message_handler import MessageHandler


class BrokerClient(ABC):
    """Abstract definition of a Broker Client.

    Will abstractly manage interaction between implementation specific message broker
    calls and higher level pub/sub features.
    """

    def __init__(self, flags: dict = dict()):
        """The default constructor.

        Args:
            flags: Dictionary of flags and values to configure the connection.
        """

        self._connection = None
        self._flags = flags

    @abstractmethod
    def connect(self, host: str, port: int, username: str, password: str):
        """Connect to the defined broker.

        Args:
            host: Broker's hostname as a string.
            port: Broker's port as a string.
            username: Username.
            password: Password.
        """
        # NOTE: The abstract base class should throw errors if this is not
        # overridden anyway. This is mainly just a placeholder.

        # Put broker connection code here
        raise NotImplementedError("connect() not implemented")

    @abstractmethod
    def is_connected(self):
        """Checks if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """

        raise NotImplementedError("is_connected() not implemented")

    @abstractmethod
    def publish(self, topic: str, payload: bytes):
        """Publishes the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish as a string.
        """
        raise NotImplementedError("publish() not implemented")

    @abstractmethod
    def subscribe(self, topics: list, handler: MessageHandler):
        """Subscribe to one or more topics over the pre-existing connection (via connect()).

        Handlers will be invoked in the order in which they were given to subscribe().

        Args:
            topics: List of strings of topics to subscribe to.
            handler: Callable to be invoked  on the incoming messages from the subscribed.
                topics.
        """
        raise NotImplementedError("subscribe() not implemented")

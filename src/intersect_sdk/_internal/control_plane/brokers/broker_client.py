from abc import ABC, abstractmethod


class BrokerClient(ABC):
    """Abstract definition of a Broker Client.

    Will abstractly manage interaction between implementation specific message broker
    calls and higher level pub/sub features.
    """

    @abstractmethod
    def connect(self) -> None:
        """
        Connect to the defined broker. Credentials should be cached in the constructor.
        """
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the defined broker."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Checks if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        ...

    @abstractmethod
    def publish(self, topic: str, payload: bytes) -> None:
        """Publishes the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish as a string.
        """
        ...

    @abstractmethod
    def subscribe(self, topic: str) -> None:
        """
        Subscribe to one or more topics over the pre-existing connection (via connect()).

        Args:
            topics: List of strings of topics to subscribe to.
        """
        ...

    @abstractmethod
    def unsubscribe(self, topic: str) -> None:
        """
        Unsubscribe from one or more topics over the pre-existing connection (via connect()).

        Args:
            topics: List of strings of topics to subscribe to.
        """
        ...

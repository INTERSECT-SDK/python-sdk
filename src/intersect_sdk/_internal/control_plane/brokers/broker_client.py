from typing import Protocol


class BrokerClient(Protocol):
    """Abstract definition of a Broker Client.

    Will abstractly manage interaction between implementation specific message broker
    calls and higher level pub/sub features.
    """

    def connect(self) -> None:
        """Connect to the defined broker. Credentials should be cached in the constructor."""
        ...

    def disconnect(self) -> None:
        """Disconnect from the defined broker."""
        ...

    def is_connected(self) -> bool:
        """Checks if there is an active connection to the broker.

        Returns:
            A boolean. True if there is a connection, False if not.
        """
        ...

    def considered_unrecoverable(self) -> bool:
        """Checks if the broker is considered to be in a state where it would be impossible to reconnect.

        Returns:
            A boolean. True if can't recover, False otherwise.
        """
        ...

    def publish(self, topic: str, payload: bytes, persist: bool) -> None:
        """Publishes the given message.

        Publish payload with the pre-existing connection (via connect()) on topic.

        Args:
            topic: The topic on which to publish the message as a string.
            payload: The message to publish, as raw bytes.
            persist:
                True = message will persist forever in associated queues until consumers are available (usually used for Userspace messages)
                False = remove message immediately if no consumers available (usually used for Event messages and Lifecycle messages)
        """
        ...

    def subscribe(self, topic: str, persist: bool) -> None:
        """Subscribe to a topic over the pre-existing connection (via connect()).

        This function should ALSO be called by reconnect handlers, and not just directly.
        When calling the function directly, it's expected that you have already connected.

        Args:
            topic: Topic to subscribe to.
            persist: Whether or not the queue subscribed to is intended to be long-lived.
        """
        ...

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from a topic over the pre-existing connection (via connect()).

        Note that it should NEVER be expected to call this function as part of routine cleanup.
        It should only be called if you want to continue staying connected to the broker,
        but do not want to continue listening for certain topics. In general, Services should
        NEVER call this, and clients should only call this to help clean up their queues.

        Args:
            topic: Topic to unsubscribe from.
        """
        ...

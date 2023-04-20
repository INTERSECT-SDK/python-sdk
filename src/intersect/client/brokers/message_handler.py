from abc import ABC, abstractmethod


class MessageHandler(ABC):
    """
    An abstract definition of a MessageHandler, which defines the business logic
    to be invoked whenever a BrokerClient receives a new message for a subscribed topic.
    """

    @abstractmethod
    def on_receive(self, topic, payload):
        """
        A function to handle each new message received.

        Args:
            topic: The topic the message was received on as a string.
            payload: The message received from the broker as a string.

        Returns:
            A boolean flag that determines whether subsequent MessageHandlers
            will have their own on_receive() functions invoked on this message.
            If True, the next MessageHandler will invoke on_receive().
            If False, no MessageHandler after this one will invoke on_receive().
        """
        raise NotImplementedError("on_receive() not implemented")

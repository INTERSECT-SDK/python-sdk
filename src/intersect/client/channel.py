# standard
import uuid
from typing import Callable

from ..messages.handlers.json_handler import JsonHandler
from ..messages.handlers.serialization_handler import SerializationHandler
from ..messages.types import IntersectMessage

# project
from ..brokers import BrokerClient
from ..brokers import MessageHandler


class Channel:
    """A broker channel.

    Channel class received from calling subscribe on the intersect client. This class should
    not be instanced directly, see IntersectClient.subscribe().

    Attributes:
        broker: BrokerClient connected to the broker in which this channel is housed.
        channel: A string containing the broker's name for the channel.
        serializer: An IntersectSerializer to be used to serialize published messages.
        id: A unique UUID4 for the channel.
    """

    class ChannelCallback(MessageHandler):
        """Handler for subscribed messages on a Channel.

        Attributes:
            callback: A Callable to invoke on received messages.
            serializer: An IntersectSerializer to decode received messages.
        """

        def __init__(
            self,
            callback: Callable[[IntersectMessage], bool],
            serializer: SerializationHandler = JsonHandler(),
        ):
            """The default constructor.

            Args:
                serializer: An IntersectSerializer to be used to deserialize received messages.
                callback: A Callable to be invoked on each received message.
            """

            self.serializer = serializer
            self.callback = callback

        def on_receive(self, topic: str, payload):
            """Handles a received message.

            Deserializes the message's payload and invokes callback on it.

            Returns:
                A boolean representing whether to pass this message to additional handlers in
                the list (True) or drop the message and perform no more processing (False).
            """

            decoded = self.serializer.deserialize(payload)
            pass_to_next_handler = self.callback(decoded)
            if not pass_to_next_handler:
                # Handle errors
                pass
            return pass_to_next_handler

    def __init__(
        self, channel: str, broker: BrokerClient, serializer: SerializationHandler = JsonHandler()
    ):
        """The default constructor.

        Args:
            channel: String representing the channel name as it is defined on the broker.
            broker: A BrokerClient to manage the connection to the broker.
            serializer: An IntersectSerializer for serializing published messages.
        """

        self.id: uuid.UUID = uuid.uuid4()
        self.channel: str = channel
        self.serializer: SerializationHandler = serializer
        self.broker: BrokerClient = broker
        self.handler: Channel.ChannelCallback

    def publish(self, message: IntersectMessage):
        """Publish an IntersectMessage to the broker.

        Args:
            message: An IntersectMessage to be published on this channel.

        Examples:
            mock_broker = Mock()
            channel = Channel("test", mock_broker)
            message = messages.Status()
            channel.publish(message)

        """
        serialized_msg = self.serializer.serialize(message)
        self.broker.publish(self.channel, serialized_msg)

    def subscribe(self, callback: Callable[[IntersectMessage], bool]):
        """Subscribe to the broker channel.

        Listen to the broker channel, invoking callback on messages received on that
        channel. Callbacks will be invoked in the order they were subscribed, and if
        any returns False after handling a message further callbacks will not be
        invoked.

        Args:
            callback: A Callable  to be invoked when a message is received. Callback is
            called with a deserialized IntersectMessage. Returns True to continue
            processing message return False to end message processing.
        """
        self.handler = Channel.ChannelCallback(callback, serializer=self.serializer)
        self.broker.subscribe([self.channel], self.handler)

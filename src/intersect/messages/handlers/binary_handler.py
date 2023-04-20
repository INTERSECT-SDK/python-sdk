from ..types import IntersectMessage
from .serialization_handler import SerializationHandler


class BinaryHandler(SerializationHandler):
    """A SerializationHandler for (de)serialization to/from bytes"""

    def __init__(self):
        """The default constructor."""

        super(BinaryHandler, self).__init__()

    def deserialize(self, data: bytes) -> IntersectMessage:
        """Deserialize binary data into a message.

        args:
            data: Bytes representing a serialized message.
        Returns:
            An IntersectMessage representation of data's contents.
        """

        wrapper = self.message_wrapper()
        wrapper.ParseFromString(data)
        msg_type = self._get_wrapped_class(wrapper.type)
        msg = msg_type()
        msg.ParseFromString(wrapper.message.encode())
        return msg

    def serialize(self, obj: IntersectMessage) -> bytes:
        """Serialize a message into binary data.

        Args:
            obj: An IntersectMessage to serialize.
        Returns:
            Bytes containing the binary representation of obj.
        """

        if type(obj) not in self.valid_message_types:
            raise TypeError("Invalid message type")

        msg = self.message_wrapper()
        msg.type = self._get_wrapped_type(obj)
        msg.message = obj.SerializeToString()
        msg.length = len(msg.message)

        return msg.SerializeToString()

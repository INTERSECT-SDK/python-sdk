from google.protobuf import text_format

from ..types import IntersectMessage
from .serialization_handler import SerializationHandler


class StringHandler(SerializationHandler):
    """A SerializationHandler for (de)serialization to/from strings"""

    def __init__(self):
        """The default constructor."""

        super(StringHandler, self).__init__()

    def deserialize(self, data: str) -> IntersectMessage:
        """Deserialize a string into a message.

        args:
            data: String containing a representation of a serialized message.
        Returns:
            An IntersectMessage representation of data's contents.
        """

        wrapper = text_format.Parse(data, self.message_wrapper())
        msg_type = self._get_wrapped_class(wrapper.type)

        return text_format.Parse(wrapper.message, msg_type())

    def serialize(self, obj: IntersectMessage) -> str:
        """Serialize a message into a string.

        Args:
            obj: An IntersectMessage to serialize.
        Returns:
            A string representation of obj.
        """

        if type(obj) not in self.valid_message_types:
            raise TypeError("Invalid message type")

        msg = self.message_wrapper()
        msg.type = self._get_wrapped_type(obj)
        msg.message = text_format.MessageToString(obj)
        msg.length = len(msg.message)

        return text_format.MessageToString(msg)

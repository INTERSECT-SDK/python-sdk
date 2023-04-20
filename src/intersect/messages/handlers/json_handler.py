from google.protobuf import json_format

from ..types import IntersectMessage
from .serialization_handler import SerializationHandler


class JsonHandler(SerializationHandler):
    """A SerializationHandler for (de)serialization to/from JSON format strings."""

    def __init__(self):
        """The default constructor."""

        super(JsonHandler, self).__init__()

    def deserialize(self, data: str) -> IntersectMessage:
        """Deserialize JSON data into a message.

        args:
            data: String containing a JSON representation of a serialized message.
        Returns:
            An IntersectMessage representation of data's contents.
        """

        wrapper = json_format.Parse(data, self.message_wrapper())
        msg_type = self._get_wrapped_class(wrapper.type)

        return json_format.Parse(wrapper.message, msg_type())

    def serialize(self, obj: IntersectMessage) -> str:
        """Serialize a message into JSON.

        Args:
            obj: An IntersectMessage to serialize.
        Returns:
            A string containing the JSON representation of obj.
        """

        if type(obj) not in self.valid_message_types:
            raise TypeError("Invalid message type")

        msg = self.message_wrapper()
        msg.type = self._get_wrapped_type(obj)
        msg.message = json_format.MessageToJson(obj)
        msg.length = len(msg.message)

        return json_format.MessageToJson(msg)

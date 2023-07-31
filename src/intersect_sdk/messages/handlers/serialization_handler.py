from .. import demo_pb2 as demo
from .. import pb_derivatives as pb
from ..types import IntersectMessage


class SerializationHandler:
    """Handler for serialization/deserialization of data."""

    def __init__(self):
        """The default constructor."""
        self.message_wrapper = demo.Generic
        self.valid_message_types = pb.valid_message_types

    def _get_wrapped_class(self, value):
        """Returns the class object for a given enumerated value

        Args:
            value: A string representation of a class name
        Returns:
            The class object corresponding to the key value.
        """
        if value not in pb.wrapped_message_by_value:
            raise TypeError("Invalid message type")
        return pb.wrapped_message_by_value[value]

    def _get_wrapped_type(self, obj):
        """Returns the enumerated value for the given type

        Args:
            obj: A class object to retrieve the name of
        Returns:
            A string containing the name of the class of obj.
        """
        return pb.message_wrapper.Type.Value(obj.DESCRIPTOR.name.upper())

    def deserialize(self, data: bytes) -> IntersectMessage:
        """Deserialize bytes into an IntersectMessage

        Args:
            data: bytes representing a serialized IntersectMessage
        Returns:
            A IntersectMessage created from the data
        """
        pass

    def serialize(self, obj: IntersectMessage) -> bytes:
        """Serialize an IntersectMessage into bytes

        Args:
            obj: An IntersectMessage to be serialized
        Returns:
            Bytes representing the serialized IntersectMessage object
        """
        pass

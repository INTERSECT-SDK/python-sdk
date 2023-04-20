from . import demo_pb2 as demo

# This has a few helpers for handling the auto-generated message types,
# converting between the actual class names and the enumerated values/keys
# for indicating the types for any wrapped message, and supporting typing.
message_wrapper = demo.Generic

_wrapped_types = set(message_wrapper.Type.keys())
_get_wrapped_type = message_wrapper.Type.Value


# Get a list of all message names and all messages that can be wrapped within
# a generic message (i.e. they are defined in the Type enum.) The enum uses all
# upper case unlike the actually class names.
all_message_names = set(demo.DESCRIPTOR.message_types_by_name.keys())
wrapped_message_names = set(name for name in all_message_names if name.upper() in _wrapped_types)


# Get the class objects and setup a dictionary for easy mapping
all_message_types = {name: getattr(demo, name) for name in all_message_names}
wrapped_messages_types = {
    name: obj for name, obj in all_message_types.items() if name in wrapped_message_names
}
wrapped_message_by_value = {
    _get_wrapped_type(name.upper()): obj for name, obj in wrapped_messages_types.items()
}


def get_wrapped_type(obj):
    """Returns the enumerated value for the given type.

    Args:
        obj: The object to get the wrapped type of.
    Returns:
        The integer value of the wrapped object from the enumeration of types.
    """
    return message_wrapper.Type.Value(obj.DESCRIPTOR.name.upper())


def get_wrapped_class(value):
    """Returns the class object for a given enumerated value.

    Args:
        value: The integer value to retrieve the corresponding class of.
    Returns:
        The class corresponding to the index value from the list of message types.
    """
    if value not in wrapped_message_by_value:
        raise TypeError("Invalid message type")
    return wrapped_message_by_value[value]


# Support for Python typing
valid_message_types = tuple(wrapped_messages_types.values())

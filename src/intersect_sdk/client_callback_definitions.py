"""Data types used in regard to client callbacks. Only relevant for Client authors."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, TypeAlias, final

from .constants import SYSTEM_OF_SYSTEM_REGEX
from .core_definitions import IntersectDataHandler, IntersectMimeType


@dataclass
class IntersectClientMessageParams:
    """The user implementing the IntersectClient class will need to return this object in order to send a message to another Service."""

    destination: Annotated[str, Field(pattern=SYSTEM_OF_SYSTEM_REGEX)]
    """
    The destination string. You'll need to know the system-of-system representation of the Service.

    Note that this should match what you would see in the schema.
    """

    operation: str
    """
    The name of the operation you want to call from the Service - this should be represented as it is in the Service's schema.
    """

    payload: Any
    """
    The raw Python object you want to have serialized as the payload.

    If you want to just use the service's default value for a request (assuming it has a default value for a request), you may set this as None.
    """

    response_content_type: IntersectMimeType = IntersectMimeType.JSON
    """
    The IntersectMimeType of your response. You'll want this to match with the ContentType of the function from the schema.

    default: IntersectMimeType.JSON
    """

    response_data_handler: IntersectDataHandler = IntersectDataHandler.MESSAGE
    """
    The IntersectDataHandler you want to use (most people can just use IntersectDataHandler.MESSAGE here, unless your data is very large)

    default: IntersectDataHandler.MESSAGE
    """


@final
class IntersectClientCallback(BaseModel):
    """The value a user should return from ALL client callback functions.

    If you do not return a value of this type (or None), this will be treated as an Exception and will break the pub-sub loop.
    """

    messages_to_send: List[IntersectClientMessageParams] = []  # noqa: FA100 (runtime annotation)
    """
    Messages to send as a result of an event or a response from a Service.
    """
    services_to_start_listening_for_events: List[  # noqa: FA100 (runtime annotation)
        Annotated[str, Field(pattern=SYSTEM_OF_SYSTEM_REGEX)]
    ] = []
    """
    Start listening to events from these services as a result of an event or a response from a Service.

    For each event in the list - if you are already listening to the event, the action will be a no-op.
    """
    services_to_stop_listening_for_events: List[  # noqa: FA100 (runtime annotation)
        Annotated[str, Field(pattern=SYSTEM_OF_SYSTEM_REGEX)]
    ] = []
    """
    Stop listening to events from these services as a result of an event or a response from a Service.

    For each event in the list - if you are not already listening to the event, the action will be a no-op.
    """

    # pydantic config
    model_config = ConfigDict(revalidate_instances='always')


INTERSECT_JSON_VALUE: TypeAlias = Union[
    List['INTERSECT_JSON_VALUE'],
    Dict[str, 'INTERSECT_JSON_VALUE'],
    str,
    bool,
    int,
    float,
    None,
]
"""
This is a simple type representation of JSON as a Python object. INTERSECT will automatically deserialize service payloads into one of these types.

(Pydantic has a similar type, "JsonValue", which should be used if you desire functionality beyond type hinting. This is strictly a type hint.)
"""


INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE = Callable[
    [str, str, bool, INTERSECT_JSON_VALUE],
    Optional[IntersectClientCallback],
]
"""
This is a callable function type which should be defined by the user.

Note: DO NOT handle serialization/deserialization yourself, the SDK will take care of this.

Params
  The SDK will send the function four arguments:
    1) The message source - this is mostly useful for your own control flow loops you write in the function
    2) The name of the operation that triggered the response from your ORIGINAL message - needed for your own control flow loops if sending multiple messages.
    3) A boolean - if True, there was an error; if False, there was not.
    4) The response, as a Python object - the type should be based on the corresponding Service's schema response.
       The Python object will already be deserialized for you. If parameter 3 was "True", then this will be the error message, as a string.
       If parameter 3 was "False", then this will be either an integer, boolean, float, string, None,
       a List[T], or a Dict[str, T], where "T" represents any of the 7 aforementioned types.

Returns
  If you want to send one or many messages in reaction to a message, or change which services you're listening to for events, the function should return an IntersectClientCallback object.

  If you are DONE listening to messages, raise a generic Exception from your function.

  If you DON'T want to send another message or modify your events, but want to continue listening for messages, you can just return None.
Raises
  Any uncaught or raised exceptions the callback function throws will terminate the INTERSECT lifecycle.
"""

INTERSECT_CLIENT_EVENT_CALLBACK_TYPE = Callable[
    [str, str, str, INTERSECT_JSON_VALUE],
    Optional[IntersectClientCallback],
]
"""
This is a callable function type which should be defined by the user.

Note: DO NOT handle serialization/deserialization yourself, the SDK will take care of this.

Params
  The SDK will send the function four arguments:
    1) The message source (the SOS representation of the Service) - this is mostly useful for your own control flow loops you write in the function
    2) The name of the operation from the service that fired the event.
    3) The name of the event.
    4) The response, as a Python object - the type should be based on the corresponding Service's event response.
       The Python object will already be deserialized for you. This will be either an integer, boolean, float, string, None,
       a List[T], or a Dict[str, T], where "T" represents any of the 7 aforementioned types.

Returns
  If you want to send one or many messages in reaction to a message, or change which services you're listening to for events, the function should return an IntersectClientCallback object.

  If you are DONE listening to messages, raise a generic Exception from your function.

  If you DON'T want to send another message or modify your events, but want to continue listening for messages, you can just return None.
Raises
  Any uncaught or raised exceptions the callback function throws will terminate the INTERSECT lifecycle.
"""

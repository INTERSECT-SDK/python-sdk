"""Core decorators (and their associated types) for INTERSECT. Only relevant for Service authors.

Users annotate their endpoints with these decorators (chiefly @intersect_message()) much as they would when
developing a traditional REST API. The decorator allows for users to
declare certain key aspects about their data, without having to delve
into the plumbing which integrates their data into other backing services.

When annotating a function with @intersect_message() or @intersect_status(), you must make sure
all function parameters and the function return value are annotated with valid types.
This is necessary for generating a schema when creating an IntersectService.
If you are not able to create a schema, the service will refuse to start.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator, validate_call
from typing_extensions import Annotated, final

from ._internal.constants import (
    BASE_EVENT_ATTR,
    BASE_RESPONSE_ATTR,
    BASE_STATUS_ATTR,
    EVENT_ATTR_KEY,
    REQUEST_CONTENT,
    RESPONSE_CONTENT,
    RESPONSE_DATA,
    SHUTDOWN_KEYS,
    STRICT_VALIDATION,
)
from .core_definitions import IntersectDataHandler, IntersectMimeType


@final
class IntersectEventDefinition(BaseModel):
    """When defining your dictionary/map of events, the values will be represented by an EventDefinition."""

    event_type: Any  # Python's "type" is not a complete representation of valid types - notably, we want to allow typing aliases. Full validation of this is expensive, so we'll postpone it until we try to generate the schema.
    """
    The data TYPE of your event. Note that any event you emit must map to this type.

    The type you provide must be parsable by Pydantic.
    """
    content_type: IntersectMimeType = IntersectMimeType.JSON
    """
    The IntersectMimeType (aka Content-Type) of your event.

    default: IntersectMimeType.JSON
    """
    data_handler: IntersectDataHandler = IntersectDataHandler.MESSAGE
    """
    The IntersectDataHandler you want to use (most people can just use IntersectDataHandler.MESSAGE here, unless your data is very large)

    default: IntersectDataHandler.MESSAGE
    """

    @field_validator('event_type', mode='after')
    @classmethod
    def _event_type_fail_fast(cls, v: Any) -> Any:
        # we need to quickly fail here because Pydantic will try to parse strings as an eval type (giant security risk),
        # and dictionaries as a Pydantic CoreSchema type (i.e. {'type': 'any'} would be valid).
        # Regarding strings - it's impossible to effectively use __future__ annotations in Python 3.8 as parameters,
        # and in Python 3.9+ you can use annotations without them being parsed as strings.
        # BaseModel objects are technically okay because Pydantic will always treat them as the type.
        # Otherwise we can just disallow a few common typings and handle the rest when trying to create a TypeAdapter.
        if isinstance(v, (int, float, bool, str, Mapping, Sequence)):
            msg = 'IntersectEventDefintion: event_type should be a type or a type alias'
            raise ValueError(msg)  # noqa: TRY004 (Pydantic convention is to raise a ValueError)
        return v

    # pydantic config
    model_config = ConfigDict(revalidate_instances='always', frozen=True)


@validate_call
def intersect_message(
    __func: Callable[..., Any] | None = None,
    /,
    *,
    events: Optional[Dict[str, IntersectEventDefinition]] = None,  # noqa: UP006, UP007 (runtime type annotation)
    ignore_keys: Optional[Set[str]] = None,  # noqa: UP006, UP007 (runtime type annotation)
    request_content_type: IntersectMimeType = IntersectMimeType.JSON,
    response_data_transfer_handler: IntersectDataHandler = IntersectDataHandler.MESSAGE,
    response_content_type: IntersectMimeType = IntersectMimeType.JSON,
    strict_request_validation: bool = False,
) -> Callable[..., Any]:
    """Use this annotation to mark your capability method as an entrypoint to external requests.

    A class method marked with this annotation has two requirements:
      1) Excluding the self-reference in the class definition, any additional parameters MUST have an entire class hierarchy of the following types (for a comprehensive overview of types, see https://docs.pydantic.dev/latest/concepts/types/):

        - Pydantic's "BaseModel" class.
        - Dataclasses (You can either use Pydantic's or the standard library's)
        - TypedDict
        - NamedTuple
        - primitive types (str, bytes, int, float, bool)
        - None
        - Union/Optional types
        - Iterable/Sequence types (list, deque, set, tuple, frozenset, etc.)
        - Mapping types (dict, Counter, OrderedDict, etc.). Regarding mapping types: the keys must be one of str/float/int, and float/int keys CANNOT use strict_request_validation=True.
        - most stdlib types, i.e. Decimal, datetime.datetime, pathlib, etc.
        - using typing_extensions "Annotated" type in conjunction with Pydantic's "Field" or various classes from the annotated_types library
        - TODO: Generators are a WORK IN PROGRESS but will eventually represent a streaming function

      You are only allowed to have one additional parameter. Functions without this parameter are assumed to take in no arguments.
      Be sure to specify the parameter type in your function signature!

      2) Your response type MUST have a class hierarchy of the same types as above. Be sure to specify the
         parameter type in your function signature! (If you do not return a response, explicitly mark your return type as "None")

    Example::

      @intersect_message()
      def some_external_function(self, request: MyBaseModelRequest) -> MyBaseModelResponse:
          # be sure to return "MyBaseModelResponse" here

    In general, if you are able to create a service from this class, you should be okay.

    Params:
      - events: dictionary of event names (strings) to IntersectEventDefninitions.
        An IntersectEventDefinition contains metadata about your event, including its type.
        Note that the type defined on the IntersectEventDefinition must be parsable by Pydantic.
        Note that while multiple functions can emit the same event name, they MUST advertise the SAME type
        for this event name.
        Inside your function, you may call "self.intersect_sdk_emit_event(event_name, event_value)" to fire off the event.
        You may call this in an inner, non-annotated function, but NOTE: EVERY function which calls this function MUST
        advertise the same event.
      - ignore_keys: Hashset of keys. The service class maintains a set of keys to ignore, and will ignore
        this function if at least one key is present in the service set.
        By default, all functions will always be allowed.
        You generally only need this if you want to forbid only a subset of functions - use
        "service.shutdown()" to disconnect from INTERSECT entirely.
        In general, you should NOT define this on functions which are just query functions;
        only set this if you are mutating INSTRUMENT or APPLICATION state.
      - request_content_type: how to deserialize incoming requests (default: JSON)
      - response_content_type: how to serialize outgoing requests (default: JSON)
      - response_data_transfer_handler: are responses going out through the message, or through another mean
        (i.e. MINIO)?
      - strict_request_validation: if this is set to True, use pydantic strict validation for requests - otherwise, use lenient validation (default: False)
        See https://docs.pydantic.dev/latest/concepts/conversion_table/ for more info about this.
        NOTE: If you are using a Mapping type (i.e. Dict) with integer or float keys, you MUST leave this on False.
    """

    def inner_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if isinstance(func, classmethod):
            msg = 'The `@classmethod` decorator cannot be used with `@intersect_message()`'
            raise TypeError(msg)
        if isinstance(func, staticmethod):
            msg = 'The `@staticmethod` decorator should be applied after `@intersect_message` (put `@staticmethod` on top)'
            raise TypeError(msg)

        @functools.wraps(func)
        def __intersect_sdk_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        setattr(__intersect_sdk_wrapper, BASE_RESPONSE_ATTR, True)
        setattr(__intersect_sdk_wrapper, REQUEST_CONTENT, request_content_type)
        setattr(__intersect_sdk_wrapper, RESPONSE_CONTENT, response_content_type)
        setattr(__intersect_sdk_wrapper, RESPONSE_DATA, response_data_transfer_handler)
        setattr(__intersect_sdk_wrapper, STRICT_VALIDATION, strict_request_validation)
        setattr(__intersect_sdk_wrapper, SHUTDOWN_KEYS, set(ignore_keys) if ignore_keys else set())
        setattr(__intersect_sdk_wrapper, EVENT_ATTR_KEY, events or {})

        return __intersect_sdk_wrapper

    if __func:
        return inner_decorator(__func)
    return inner_decorator


# TODO - consider forcing intersect_status endpoints to send Messages and JSON responses.
@validate_call
def intersect_status(
    __func: Callable[..., Any] | None = None,
    /,
    *,
    response_data_transfer_handler: IntersectDataHandler = IntersectDataHandler.MESSAGE,
    response_content_type: IntersectMimeType = IntersectMimeType.JSON,
) -> Any:
    """Use this annotation to mark your capability method as a status retrieval function.

    You may ONLY mark ONE function as a status retrieval function. It's advisable to have one.

    Your status retrieval function may not have any parameters (other than "self"). Return annotation rules mirror
    the typing rules for @intersect_message().

    A status message MUST NOT send events out. It should be a simple query of the general service (no specifics).

    Params:
        - response_content_type: how to serialize outgoing requests (default: JSON)
        - response_data_transfer_handler: are responses going out through the message, or through another mean
          (i.e. MINIO)?
    """

    def inner_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if isinstance(func, classmethod):
            msg = 'The `@classmethod` decorator cannot be used with `@intersect_status()`'
            raise TypeError(msg)
        if isinstance(func, staticmethod):
            msg = 'The `@staticmethod` decorator should be applied after `@intersect_status` (put `@staticmethod` on top)'
            raise TypeError(msg)

        @functools.wraps(func)
        def __intersect_sdk_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        setattr(__intersect_sdk_wrapper, BASE_STATUS_ATTR, True)
        setattr(__intersect_sdk_wrapper, REQUEST_CONTENT, IntersectMimeType.JSON)
        setattr(__intersect_sdk_wrapper, RESPONSE_CONTENT, response_content_type)
        setattr(__intersect_sdk_wrapper, RESPONSE_DATA, response_data_transfer_handler)
        setattr(__intersect_sdk_wrapper, STRICT_VALIDATION, False)
        setattr(__intersect_sdk_wrapper, SHUTDOWN_KEYS, set())

        return __intersect_sdk_wrapper

    if __func:
        return inner_decorator(__func)
    return inner_decorator


@validate_call
def intersect_event(
    *,
    events: Annotated[Dict[str, IntersectEventDefinition], Field(min_length=1)],  # noqa: UP006 (runtime type annotation)
) -> Callable[..., Any]:
    """Use this annotation to mark a function as an event emitter.

    This annotation is meant to be used in conjunction with secondary threads that you start on your CapabilityImplementation.
    You should ONLY annotate the function which is the direct thread target.

    Note that you should NOT use this annotation in combination with any other annotation. If you are exposing an endpoint
    which ALSO emits messages, use @intersect_message(events={...}) instead.

    Also note that the events you register here should be compatible with all events registered on @intersect_message annotations.

    Params:
      - events: dictionary of event names (strings) to IntersectEventDefninitions.
        You must declare at least one definition.
        An IntersectEventDefinition contains metadata about your event, including its type.
        Note that the type defined on the IntersectEventDefinition must be parsable by Pydantic.
        Note that while multiple functions can emit the same event name, they MUST advertise the SAME type
        for this event name.
        Inside your function, you may call "self.intersect_sdk_emit_event(event_name, event_value)" to fire off the event.
        You may call this in an inner, non-annotated function, but NOTE: EVERY function which calls this function MUST
        advertise the same event.
    """

    def inner_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # NOTE: we don't actually care how users decorate their @intersect_event functions, because we don't call them.

        @functools.wraps(func)
        def __intersect_sdk_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        setattr(__intersect_sdk_wrapper, BASE_EVENT_ATTR, True)
        setattr(__intersect_sdk_wrapper, EVENT_ATTR_KEY, events)

        return __intersect_sdk_wrapper

    return inner_decorator

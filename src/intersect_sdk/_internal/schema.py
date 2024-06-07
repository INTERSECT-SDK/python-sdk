"""Internal utilities for schema generation we don't want exposed to users."""

from __future__ import annotations

import inspect
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Mapping,
    NamedTuple,
    get_origin,
)

from pydantic import PydanticUserError, TypeAdapter
from typing_extensions import TypeAliasType

from ..version import version_string
from .constants import (
    BASE_EVENT_ATTR,
    BASE_RESPONSE_ATTR,
    BASE_STATUS_ATTR,
    EVENT_ATTR_KEY,
    REQUEST_CONTENT,
    RESPONSE_CONTENT,
    RESPONSE_DATA,
)
from .event_metadata import EventMetadata, definition_metadata_differences
from .function_metadata import FunctionMetadata
from .logger import logger
from .messages.event import EventMessageHeaders
from .messages.userspace import UserspaceMessageHeader
from .pydantic_schema_generator import GenerateTypedJsonSchema
from .utils import die

if TYPE_CHECKING:
    from pydantic.json_schema import JsonSchemaMode

    from ..capability.base import IntersectBaseCapabilityImplementation
    from ..config.shared import HierarchyConfig
    from ..core_definitions import IntersectDataHandler
    from ..service_definitions import IntersectEventDefinition

ASYNCAPI_VERSION = '2.6.0'

# TypeAdapter works on a variety of types, try to document them here
SCHEMA_HELP_MSG = """
Valid types include any class extending from pydantic.BaseModel, dataclasses, primitives, List, Set, FrozenSet, Iterable, Dict, Mapping, Tuple, NamedTuple, TypedDict, Optional, and Union.
A complete list of valid types can be found at the following links:
For a general overview, https://docs.pydantic.dev/latest/concepts/types/
For standard library types, https://docs.pydantic.dev/latest/api/standard_library_types/
For Pydantic specific type, https://docs.pydantic.dev/latest/api/types/
For networking types, https://docs.pydantic.dev/latest/api/networks/
For a complete reference, https://docs.pydantic.dev/latest/concepts/conversion_table
"""


class _FunctionAnalysisResult(NamedTuple):
    """private class generated from static analysis of function."""

    capability_name: str
    method_name: str
    method: Callable[[Any], Any]
    """raw method is for inspecting attributes"""
    min_args: int
    """this usually just means number of implicit arguments to a function. Note that for events we currently don't use this.

    the maximum number of args can always be derived from this, so don't bother storing it
    """


def _function_static_analysis(
    capability: type[IntersectBaseCapabilityImplementation],
    name: str,
    method: Any,
    check_method_type: bool = True,
) -> _FunctionAnalysisResult:
    """This performs generic, simple static analysis, which can be used across annotations."""
    if not callable(method):
        die(
            f'On class attribute "{name}", INTERSECT annotation should only be used on callable functions, and should be applied first (put it at the bottom)'
        )
    min_args = 0xFF  # max args Python allows, excepting varargs
    if check_method_type:
        static_attr = inspect.getattr_static(capability, name)
        if isinstance(static_attr, classmethod):
            die(
                f'On class attribute "{name}", INTERSECT annotations cannot be used with @classmethod'
            )
        min_args = int(not isinstance(static_attr, staticmethod))
    return _FunctionAnalysisResult(capability.__name__, name, method, min_args)


def _get_functions(
    capability: type[IntersectBaseCapabilityImplementation],
) -> tuple[
    _FunctionAnalysisResult | None,
    list[_FunctionAnalysisResult],
    list[_FunctionAnalysisResult],
]:
    """Inspect all functions, and check that annotated functions are not classmethods (which are always a mistake) and are callable.

    In Python, staticmethods can be called from an instance; since they are more performant than instance methods, they should be allowed.

    Params:
      - capability - type of user's class

    Yields:
      - name of function
      - the function
      - minimum number of arguments (0 if staticmethod, 1 if instance method)
    """
    intersect_status = None
    intersect_messages = []
    intersect_events = []

    for name in dir(capability):
        method = getattr(capability, name)
        if hasattr(method, BASE_EVENT_ATTR):
            intersect_events.append(
                _function_static_analysis(
                    capability,
                    name,
                    method,
                    False,
                )
            )
        elif hasattr(method, BASE_RESPONSE_ATTR):
            intersect_messages.append(_function_static_analysis(capability, name, method))
        elif hasattr(method, BASE_STATUS_ATTR):
            if intersect_status is not None:
                die(
                    f"Class '{capability.__name__}' should only have one function annotated with the @intersect_status() decorator."
                )
            intersect_status = _function_static_analysis(capability, name, method)

    if intersect_status is None:
        logger.warning(
            f"Class '{capability.__name__}' has no function annotated with the @intersect_status() decorator. No status information will be provided when sending status messages."
        )
    if not intersect_messages and not intersect_events:
        die(
            f"No intersect annotations detected on class '{capability.__name__}'. Please annotate at least one entrypoint with '@intersect_message()', or one event-emitting function with '@intersect_event()' ."
        )
    return intersect_status, intersect_messages, intersect_events


def _merge_schema_definitions(
    adapter: TypeAdapter[Any],
    schemas: dict[str, Any],
    annotation: type,
    mode: JsonSchemaMode,
) -> dict[str, Any]:
    """This contains the core logic for generating a schema from the user's type definitions.

    This accomplishes two things after generating the schema:
    1) merges new schema definitions into the main schemas dictionary (NOTE: the schemas param is mutated)
    2) returns the value which will be represented in the channel payload

    NOTE: Before modifying this function, you should have EXTENSIVE knowledge on how Pydantic handles
    various types internally.
    """
    schema = adapter.json_schema(
        ref_template='#/components/schemas/{model}',
        schema_generator=GenerateTypedJsonSchema,
        mode=mode,
    )
    definitions = schema.pop('$defs', None)
    if definitions:
        schemas.update(definitions)

    # when Pydantic generates schemas, it likes to put explicit classes into $defs
    # TypeAliasType annotations always get their own definitions
    if isinstance(annotation, TypeAliasType):
        schemas[annotation.__name__] = schema
        return {'$ref': f'#/components/schemas/{annotation.__name__}'}
    schema_type = schema.get('type')
    if schema_type == 'object':
        # Dict, OrderedDict, and Mapping lack a user-defined label, so just return the schema
        ann_origin = get_origin(annotation)
        if inspect.isclass(ann_origin) and issubclass(ann_origin, Mapping):
            return schema
        schemas[annotation.__name__] = schema
        return {'$ref': f'#/components/schemas/{annotation.__name__}'}
    if schema_type == 'array':
        # NamedTuples get their own definitions, all other array types do not
        if (
            inspect.isclass(annotation)
            and issubclass(annotation, tuple)
            and hasattr(annotation, '_fields')
        ):
            schemas[annotation.__name__] = schema
            return {'$ref': f'#/components/schemas/{annotation.__name__}'}
        return schema
    if 'enum' in schema or 'const' in schema:
        # Enum typings get their own definitions, Literals are inlined
        if inspect.isclass(annotation) and issubclass(annotation, Enum):
            schemas[annotation.__name__] = schema
            return {'$ref': f'#/components/schemas/{annotation.__name__}'}
        return schema
    return schema


def _status_fn_schema(
    status_info: _FunctionAnalysisResult, schemas: dict[str, Any]
) -> tuple[
    str,
    Callable[[Any], Any],
    dict[str, Any],
    TypeAdapter[Any],
]:
    """Main status function logic. Should only be called if the status function actually exists.

    Returns a tuple of:
    - The name of the status function
    - The status function itself
    - The status function's schema
    - The TypeAdapter to use for serializing outgoing responses
    """
    capability_name, status_fn_name, status_fn, min_params = status_info
    status_signature = inspect.signature(status_fn)
    method_params = tuple(status_signature.parameters.values())
    if len(method_params) != min_params or any(
        p.kind not in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY) for p in method_params
    ):
        die(
            f"On capability '{capability_name}', capability status function '{status_fn_name}' should have no parameters other than 'self' (unless a staticmethod), and should not use keyword or variable length arguments (i.e. '*', *args, **kwargs)."
        )
    if status_signature.return_annotation is inspect.Signature.empty:
        die(
            f"On capability '{capability_name}', capability status function '{status_fn_name}' should have a valid return annotation."
        )
    try:
        status_adapter = TypeAdapter(status_signature.return_annotation)
        return (
            status_fn_name,
            status_fn,
            _merge_schema_definitions(
                status_adapter,
                schemas,
                status_signature.return_annotation,
                'serialization',
            ),
            status_adapter,
        )
    except PydanticUserError as e:
        die(
            f"On capability '{capability_name}', return annotation '{status_signature.return_annotation}' on function '{status_fn_name}' is invalid.\n{e}"
        )


def _add_events(
    capability_name: str,
    function_name: str,
    schemas: dict[str, Any],
    event_schemas: dict[str, Any],
    event_metadatas: dict[str, EventMetadata],
    function_events: dict[str, IntersectEventDefinition],
    excluded_data_handlers: set[IntersectDataHandler],
) -> None:
    """Common logic for adding events to both the schema and the implementation/validation mapping."""
    for event_key, event_definition in function_events.items():
        if event_key in event_metadatas:
            metadata_value = event_metadatas[event_key]
            differences_from_cache = definition_metadata_differences(
                event_definition, metadata_value
            )
            if differences_from_cache:
                diff_str = '\n'.join(
                    f'{d[0]} mismatch: current={d[1]}, previous={d[2]}'
                    for d in differences_from_cache
                )
                die(
                    f"On capability '{capability_name}', event key '{event_key}' on function '{function_name}' was previously defined differently. \n{diff_str}\n"
                )
            metadata_value.operations.add(function_name)
        else:
            if event_definition.data_handler in excluded_data_handlers:
                die(
                    f"On capability '{capability_name}', function '{function_name}' should not set data_handler as {event_definition.data_handler} unless an instance is configured in IntersectConfig.data_stores ."
                )
            try:
                event_adapter: TypeAdapter[Any] = TypeAdapter(event_definition.event_type)
                event_schemas[event_key] = _merge_schema_definitions(
                    event_adapter,
                    schemas,
                    event_definition.event_type,
                    'serialization',
                )
                event_metadatas[event_key] = EventMetadata(
                    type=event_definition.event_type,
                    type_adapter=event_adapter,
                    operations={function_name},
                    content_type=event_definition.content_type,
                    data_transfer_handler=event_definition.data_handler,
                )
            except PydanticUserError as e:
                die(
                    f"On capability '{capability_name}', event key '{event_key}' on function '{function_name}' has an invalid value in the events mapping.\n{e}"
                )


def _introspection_baseline(
    capability: type[IntersectBaseCapabilityImplementation],
    excluded_data_handlers: set[IntersectDataHandler],
) -> tuple[
    dict[Any, Any],  # $defs for schemas (common)
    tuple[
        str | None, dict[str, Any] | None, TypeAdapter[Any] | None
    ],  # status function name, schema, type adapter
    dict[str, dict[str, dict[str, Any]]],  # endpoint schemas
    dict[str, FunctionMetadata],  # endpoint functionality
    dict[str, Any],  # event schemas
    dict[str, EventMetadata],  # event functionality
]:
    """This function does the bulk of introspection, and also validates the user's capability.

    Basic logic:

    - Capabilities should implement functions which represent entrypoints
    - Each entrypoint should be annotated with @intersect_message() (this sets a hidden attribute)
    - Entrypoint functions should either have no parameters, or they should
      describe all their parameters in one BaseModel-derived class.
      (NOTE: maybe allow for some other input formats?)
    """
    # global schema variables
    schemas: dict[Any, Any] = {}
    channels: dict[str, Any] = {}
    event_schemas: dict[str, Any] = {}
    # global implementation variables
    function_map = {}
    event_metadatas: dict[str, EventMetadata] = {}

    status_func, response_funcs, event_funcs = _get_functions(capability)

    # parse functions
    for capability_name, name, method, min_params in response_funcs:
        # TODO - I'm placing this here for now because we'll eventually want to capture data plane and broker configs in the schema.
        # (It's possible we may want to separate the backing service schema from the application logic, but it's unlikely.)
        # At the moment, we're just validating that users can support their response_data_handler property.
        # (We probably want to eventually deprecate/remove that property.)
        data_handler = getattr(method, RESPONSE_DATA)
        if data_handler in excluded_data_handlers:
            die(
                f"On capability '{capability_name}', function '{name}' should not set response_data_type as {data_handler} unless an instance is configured in IntersectConfig.data_stores ."
            )

        docstring = inspect.cleandoc(method.__doc__) if method.__doc__ else None
        signature = inspect.signature(method)
        method_params = tuple(signature.parameters.values())
        return_annotation = signature.return_annotation
        if (
            len(method_params) < min_params
            or len(method_params) > min_params + 1
            or any(
                p.kind not in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY) for p in method_params
            )
        ):
            die(
                f"On capability '{capability_name}', function '{name}' should have 'self' (unless a staticmethod) and zero or one additional parameters, and should not use keyword or variable length arguments (i.e. '*', *args, **kwargs)."
            )

        # The schema format should be hard-coded and determined based on how Pydantic parses the schema.
        # See https://docs.pydantic.dev/latest/concepts/json_schema/ for that specification.
        channels[name] = {
            'publish': {
                'message': {
                    'schemaFormat': f'application/vnd.aai.asyncapi+json;version={ASYNCAPI_VERSION}',
                    'contentType': getattr(method, REQUEST_CONTENT).value,
                    'traits': {'$ref': '#/components/messageTraits/commonHeaders'},
                }
            },
            'subscribe': {
                'message': {
                    'schemaFormat': f'application/vnd.aai.asyncapi+json;version={ASYNCAPI_VERSION}',
                    'contentType': getattr(method, RESPONSE_CONTENT).value,
                    'traits': {'$ref': '#/components/messageTraits/commonHeaders'},
                }
            },
        }
        if docstring:
            channels[name]['publish']['description'] = docstring
            channels[name]['subscribe']['description'] = docstring

        # this block handles request params
        if len(method_params) == min_params + 1:
            parameter = method_params[-1]
            annotation = parameter.annotation
            # Pydantic BaseModels require annotations even if using a default value, so we'll remain consistent.
            if annotation is inspect.Parameter.empty:
                die(
                    f"On capability '{capability_name}', parameter '{parameter.name}' type annotation on function '{name}' missing. {SCHEMA_HELP_MSG}"
                )
            # rationale for disallowing function default values:
            # https://docs.pydantic.dev/latest/concepts/validation_decorator/#using-field-to-describe-function-arguments
            # (in general, default_factory is not something which should be used with user parameters)
            # also makes TypeAdapters considerably easier to construct
            if parameter.default is not inspect.Parameter.empty:
                die(
                    f"On capability '{capability_name}', parameter '{parameter.name}' should not use a default value in the function parameter (use 'typing_extensions.Annotated[TYPE, pydantic.Field(default=<DEFAULT>)]' instead - 'default_factory' is an acceptable, mutually exclusive argument to 'Field')."
                )
            try:
                function_cache_request_adapter = TypeAdapter(annotation)
                channels[name]['subscribe']['message']['payload'] = _merge_schema_definitions(
                    function_cache_request_adapter,
                    schemas,
                    annotation,
                    'validation',
                )
            except PydanticUserError as e:
                die(
                    f"On capability '{capability_name}', parameter '{parameter.name}' type annotation '{annotation}' on function '{name}' is invalid\n{e}"
                )

        else:
            function_cache_request_adapter = None

        # this block handles response parameters
        if return_annotation is inspect.Signature.empty:
            die(
                f"On capability '{capability_name}', return type annotation on function '{name}' missing. {SCHEMA_HELP_MSG}"
            )
        try:
            function_cache_response_adapter = TypeAdapter(return_annotation)
            channels[name]['publish']['message']['payload'] = _merge_schema_definitions(
                function_cache_response_adapter,
                schemas,
                return_annotation,
                'serialization',
            )
        except PydanticUserError as e:
            die(
                f"On capability '{capability_name}', return annotation '{return_annotation}' on function '{name}' is invalid.\n{e}"
            )

        # final function mapping
        function_map[name] = FunctionMetadata(
            method,
            function_cache_request_adapter,
            function_cache_response_adapter,
        )

        # this block handles events associated with intersect_messages (implies command pattern)
        function_events: dict[str, IntersectEventDefinition] = getattr(method, EVENT_ATTR_KEY)
        _add_events(
            capability_name,
            name,
            schemas,
            event_schemas,
            event_metadatas,
            function_events,
            excluded_data_handlers,
        )
        channels[name]['events'] = list(function_events.keys())

    # parse global schemas
    for capability_name, name, method, _ in event_funcs:
        _add_events(
            capability_name,
            name,
            schemas,
            event_schemas,
            event_metadatas,
            getattr(method, EVENT_ATTR_KEY),
            excluded_data_handlers,
        )

    status_fn_name, status_fn, status_fn_schema, status_fn_type_adapter = (
        _status_fn_schema(status_func, schemas) if status_func else (None, None, None, None)
    )
    # this conditional allows for the status function to also be called like a message
    if status_fn_type_adapter and status_fn and status_fn_name:
        function_map[status_fn_name] = FunctionMetadata(
            status_fn,
            None,
            status_fn_type_adapter,
        )

    return (
        schemas,
        (status_fn_name, status_fn_schema, status_fn_type_adapter),
        channels,
        function_map,
        event_schemas,
        event_metadatas,
    )


def get_schema_and_functions_from_capability_implementation(
    capability_type: type[IntersectBaseCapabilityImplementation],
    capability_name: HierarchyConfig,
    excluded_data_handlers: set[IntersectDataHandler],
) -> tuple[
    dict[str, Any],
    dict[str, FunctionMetadata],
    dict[str, EventMetadata],
    str | None,
    TypeAdapter[Any] | None,
]:
    """This function generates the core AsyncAPI schema, and the core mappings which are derived from the schema.

    In-depth introspection is handled later on.
    """
    (
        schemas,
        (status_fn_name, status_schema, status_type_adapter),
        channels,
        function_map,
        events,
        event_map,
    ) = _introspection_baseline(capability_type, excluded_data_handlers)

    asyncapi_spec = {
        'asyncapi': ASYNCAPI_VERSION,
        'x-intersect-version': version_string,
        'info': {
            'title': capability_name.hierarchy_string('.'),
            'version': '0.0.0',  # NOTE: this will be modified by INTERSECT CORE, users do not manage their schema versions
        },
        # applies to how an incoming message payload will be parsed.
        # can be changed per channel
        'defaultContentType': 'application/json',
        'channels': channels,
        'events': events,
        'components': {
            'schemas': schemas,
            'messageTraits': {
                # this is where we can define our message headers
                'commonHeaders': {
                    'messageHeaders': TypeAdapter(UserspaceMessageHeader).json_schema(
                        ref_template='#/components/messageTraits/commonHeaders/userspaceHeaders/$defs/{model}',
                        mode='serialization',
                    ),
                    'eventHeaders': TypeAdapter(EventMessageHeaders).json_schema(
                        ref_template='#/components/messageTraits/commonHeaders/eventHeaders/$defs/{model}',
                        mode='serialization',
                    ),
                }
            },
        },
    }
    if capability_type.__doc__:
        asyncapi_spec['info']['description'] = inspect.cleandoc(capability_type.__doc__)  # type: ignore[index]

    if status_schema:
        asyncapi_spec['status'] = status_schema

    """
    TODO - might want to include these fields
    "securitySchemes": {},
    "operationTraits": {},
    "externalDocumentation": {
        "url": "https://example.com",  # REQUIRED
    },
    """

    return asyncapi_spec, function_map, event_map, status_fn_name, status_type_adapter

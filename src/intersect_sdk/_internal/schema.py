"""Internal utilities for schema generation we don't want exposed to users."""

from __future__ import annotations

import inspect
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Mapping,
    get_origin,
)

from pydantic import PydanticUserError, TypeAdapter
from typing_extensions import TypeAliasType

from .constants import BASE_ATTR, BASE_STATUS_ATTR, REQUEST_CONTENT, RESPONSE_CONTENT, RESPONSE_DATA
from .function_metadata import FunctionMetadata
from .logger import logger
from .pydantic_schema_generator import GenerateTypedJsonSchema
from .utils import die

if TYPE_CHECKING:
    from pydantic.json_schema import JsonSchemaMode

    from ..annotations import IntersectDataHandler

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


def _get_functions(
    capability: type, attr: str
) -> Generator[tuple[str, Callable[[Any], Any], int], None, None]:
    """Inspect all functions, and check that annotated functions are not classmethods (which are always a mistake) and are callable.

    In Python, staticmethods can be called from an instance; since they are more performant than instance methods, they should be allowed.

    Params:
      - capability - type of user's class
      - attr: hidden attribute we want to lookup on the user's function

    Yields:
      - name of function
      - the function
      - minimum number of arguments (0 if staticmethod, 1 if instance method)
    """
    for name in dir(capability):
        method = getattr(capability, name)
        if hasattr(method, attr):
            if not callable(method):
                die(
                    'INTERSECT annotation should only be used on callable functions, and should be applied first (put it at the bottom)'
                )
            static_attr = inspect.getattr_static(capability, name)
            if isinstance(static_attr, classmethod):
                die('INTERSECT annotations cannot be used with @classmethod')
            yield name, method, int(not isinstance(static_attr, staticmethod))


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
    capability: type, schemas: dict[str, Any]
) -> tuple[
    str | None,
    Callable[[Any], Any] | None,
    dict[str, Any] | None,
    TypeAdapter[Any] | None,
]:
    """Main status function logic.

    Returns a tuple of:
    - The name of the status function, if it exists (else None)
    - The status function itself, if it exists (else, None)
    - If the status function exists, the function's schema. else, None
    - The TypeAdapter to use for serializing outgoing responses, if the status function exists; else, None
    """
    status_fns = tuple(_get_functions(capability, BASE_STATUS_ATTR))
    if len(status_fns) > 1:
        die(
            f"Class '{capability.__name__}' should only have one function annotated with the @intersect_status() decorator."
        )
    if len(status_fns) == 0:
        logger.warning(
            f"Class '{capability.__name__}' has no function annotated with the @intersect_status() decorator. No status information will be provided when sending status messages."
        )
        return None, None, None, None
    status_fn_name, status_fn, min_params = status_fns[0]
    status_signature = inspect.signature(status_fn)
    method_params = tuple(status_signature.parameters.values())
    if len(method_params) != min_params or any(
        p.kind not in (p.POSITIONAL_OR_KEYWORD, p.POSITIONAL_ONLY) for p in method_params
    ):
        die(
            f"On capability '{capability.__name__}', capability status function '{status_fn_name}' should have no parameters other than 'self' (unless a staticmethod), and should not use keyword or variable length arguments (i.e. '*', *args, **kwargs)."
        )
    if status_signature.return_annotation is inspect.Signature.empty:
        die(
            f"On capability '{capability.__name__}', capability status function '{status_fn_name}' should have a valid return annotation."
        )
    try:
        status_adapter = TypeAdapter(status_signature.return_annotation)
        return (
            status_fn_name,
            status_fn,
            _merge_schema_definitions(
                status_adapter, schemas, status_signature.return_annotation, 'serialization'
            ),
            status_adapter,
        )
    except PydanticUserError as e:
        die(
            f"On capability '{capability.__name__}', return annotation '{status_signature.return_annotation}' on function '{status_fn_name}' is invalid.\n{e}"
        )


def get_schemas_and_functions(
    capability: type,
    excluded_data_handlers: set[IntersectDataHandler],
) -> tuple[
    dict[Any, Any],
    tuple[str | None, dict[str, Any] | None, TypeAdapter[Any] | None],
    dict[str, dict[str, dict[str, dict[str, Any]]]],
    dict[str, FunctionMetadata],
]:
    """This function does the bulk of introspection, and also validates the user's capability.

    Basic logic:

    - Capabilities should implement functions which represent entrypoints
    - Each entrypoint should be annotated with @intersect_message() (this sets a hidden attribute)
    - Entrypoint functions should either have no parameters, or they should
      describe all their parameters in one BaseModel-derived class.
      (NOTE: maybe allow for some other input formats?)
    """
    function_map = {}
    schemas: dict[Any, Any] = {}
    channels = {}

    for name, method, min_params in _get_functions(capability, BASE_ATTR):
        # TODO - I'm placing this here for now because we'll eventually want to capture data plane and broker configs in the schema.
        # (It's possible we may want to separate the backing service schema from the application logic, but it's unlikely.)
        # At the moment, we're just validating that users can support their response_data_handler property.
        # (We probably want to eventually deprecate/remove that property.)
        data_handler = getattr(method, RESPONSE_DATA)
        if data_handler in excluded_data_handlers:
            die(
                f"On capability '{capability.__name__}', function '{name}' should not set response_data_type as {data_handler} unless an instance is configured in IntersectConfig.data_stores ."
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
                f"On capability '{capability.__name__}', function '{name}' should have 'self' (unless a staticmethod) and zero or one additional parameters, and should not use keyword or variable length arguments (i.e. '*', *args, **kwargs)."
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
            channels[name]['publish']['description'] = docstring  # type: ignore[assignment]
            channels[name]['subscribe']['description'] = docstring  # type: ignore[assignment]

        # this block handles request params
        if len(method_params) == min_params + 1:
            parameter = method_params[-1]
            annotation = parameter.annotation
            # Pydantic BaseModels require annotations even if using a default value, so we'll remain consistent.
            if annotation is inspect.Parameter.empty:
                die(
                    f"On capability '{capability.__name__}', parameter '{parameter.name}' type annotation on function '{name}' missing. {SCHEMA_HELP_MSG}"
                )
            # rationale for disallowing function default values:
            # https://docs.pydantic.dev/latest/concepts/validation_decorator/#using-field-to-describe-function-arguments
            # (in general, default_factory is not something which should be used with user parameters)
            # also makes TypeAdapters considerably easier to construct
            if parameter.default is not inspect.Parameter.empty:
                die(
                    f"On capability '{capability.__name__}', parameter '{parameter.name}' should not use a default value in the function parameter (use 'typing_extensions.Annotated[TYPE, pydantic.Field(default=<DEFAULT>)]' instead - 'default_factory' is an acceptable, mutually exclusive argument to 'Field')."
                )
            try:
                function_cache_request_adapter = TypeAdapter(annotation)
                channels[name]['subscribe']['message']['payload'] = _merge_schema_definitions(
                    function_cache_request_adapter, schemas, annotation, 'validation'
                )
            except PydanticUserError as e:
                die(
                    f"On capability '{capability.__name__}', parameter '{parameter.name}' type annotation '{annotation}' on function '{name}' is invalid\n{e}"
                )

        else:
            function_cache_request_adapter = None

        # this block handles response parameters
        if return_annotation is inspect.Signature.empty:
            die(
                f"On capability '{capability.__name__}', return type annotation on function '{name}' missing. {SCHEMA_HELP_MSG}"
            )
        try:
            function_cache_response_adapter = TypeAdapter(return_annotation)
            channels[name]['publish']['message']['payload'] = _merge_schema_definitions(
                function_cache_response_adapter, schemas, return_annotation, 'serialization'
            )
        except PydanticUserError as e:
            die(
                f"On capability '{capability.__name__}', return annotation '{return_annotation}' on function '{name}' is invalid.\n{e}"
            )

        function_map[name] = FunctionMetadata(
            method,
            function_cache_request_adapter,
            function_cache_response_adapter,
        )

    # potentially add status function to function map, but check for intersect_message first
    if len(function_map) == 0:
        die(
            f"No entrypoints detected on class '{capability.__name__}'. Please annotate at least one entrypoint with '@intersect_message()' ."
        )

    status_fn_name, status_fn, status_fn_schema, status_fn_type_adapter = _status_fn_schema(
        capability, schemas
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
    )

"""
This module is responsible for generating the core interface definitions of any service. There are two things to generate:

###
Schema
###

JSON schema advertises the interfaces to other systems. This is necessary for creating scientific campaigns, and the schema
is extensible to other clients.

Parts of the schema will be generated from users' own definitions. Functions are represented under "channels",
while Pydantic models defined by users and used as request or response types in their functions will have their schemas generated here.

There are also several parameters mainly for use by the central INTERSECT microservices, largely encapsulated from users.

###
Code Interface
###

When external systems send a message to this system, there are two important things in determining what executes: an operation id string,
and a payload which can be serialized into an auto-validated object. The operation id string is what can be mapped into various function definitions.

Users are able to define their response and request content-types, as well as their response data platform, for each exposed function (on the annotation).

The SDK needs to be able to dynamically look up functions, validate the request structure and request parameters, and handle responses.
"""

import inspect
from enum import Enum
from typing import Any, Callable, Dict, Generator, Mapping, Optional, Tuple, Type, get_origin

from pydantic import PydanticUserError, TypeAdapter

from ._internal.constants import BASE_ATTR, BASE_STATUS_ATTR, REQUEST_CONTENT, RESPONSE_CONTENT
from ._internal.function_metadata import FunctionMetadata
from ._internal.logger import logger
from ._internal.messages.userspace import UserspaceMessageHeader
from ._internal.utils import die
from .config.shared import HierarchyConfig
from .version import __version__

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


def _get_functions(capability: Type, attr: str) -> Generator[Tuple[str, Callable], None, None]:
    for name in dir(capability):
        method = getattr(capability, name)
        if callable(method) and hasattr(method, attr):
            yield name, method


def _merge_schema_definitions(
    adapter: TypeAdapter, schemas: Dict[str, Any], annotation: Type
) -> Dict[str, Any]:
    """
    This accomplishes two things after generating the schema:
    1) merges new schema definitions into the main schemas dictionary (NOTE: the schemas param is mutated)
    2) returns the value which will be represented in the channel payload
    """
    try:
        schema = adapter.json_schema(ref_template='#/components/schemas/{model}')
    except PydanticUserError as e:
        raise e
    definitions = schema.pop('$defs', None)
    if definitions:
        schemas.update(definitions)

    # when Pydantic generates schemas, it likes to put explicit classes into $defs
    schema_type = schema.get('type')
    if schema_type == 'object':
        try:
            # Dict, OrderedDict, and Mapping lack a user-defined label, so just return the schema
            if issubclass(get_origin(annotation), Mapping):
                return schema
        except TypeError:
            pass
        schemas[annotation.__name__] = schema
        return {'$ref': f'#/components/schemas/{annotation.__name__}'}
    if schema_type == 'array':
        try:
            # NamedTuples get their own definitions, all other array types do not
            if issubclass(annotation, Tuple) and hasattr(annotation, '_fields'):
                schemas[annotation.__name__] = schema
                return {'$ref': f'#/components/schemas/{annotation.__name__}'}
        except TypeError:
            pass
    elif 'enum' in schema or 'const' in schema:
        # Enum typings get their own definitions, Literals are inlined
        try:
            if issubclass(annotation, Enum):
                schemas[annotation.__name__] = schema
                return {'$ref': f'#/components/schemas/{annotation.__name__}'}
        except TypeError:
            pass
    return schema


def _status_fn_schema(
    capability: Type, schemas: Dict[str, Any]
) -> Tuple[Optional[str], Optional[Dict[str, Any]], Optional[TypeAdapter]]:
    status_fns = tuple(_get_functions(capability, BASE_STATUS_ATTR))
    if len(status_fns) > 1:
        die(
            f"Class '{capability.__name__}' should only have one function annotated with the @intersect_status decorator."
        )
    if len(status_fns) == 0:
        logger.warn(
            f"Class '{capability.__name__}' has no function annotated with the @intersect_status decorator. No status information will be provided when sending status messages."
        )
        return None, None, TypeAdapter(None)
    status_fn_name, status_fn = status_fns[0]
    status_signature = inspect.signature(status_fn)
    if len(status_signature.parameters) != 1:
        die(
            f"On capability '{capability.__name__}', capability status function '{status_fn_name}' should have no parameters other than 'self'"
        )
    if status_signature.return_annotation is inspect.Signature.empty:
        die(
            f"On capability '{capability.__name__}', capability status function '{status_fn_name}' should have a valid return annotation."
        )
    try:
        status_adapter = TypeAdapter(status_signature.return_annotation)
        return (
            status_fn_name,
            _merge_schema_definitions(status_adapter, schemas, status_signature.return_annotation),
            status_adapter,
        )
    except PydanticUserError as e:
        die(
            f"On capability '{capability.__name__}', return annotation '{status_signature.return_annotation.__name__}' on function '{status_fn_name}' cannot be used.\n{e}"
        )


def _get_schemas_and_functions(
    capability: Type,
) -> Tuple[
    Dict[str, Any],
    Tuple[Optional[str], Optional[Dict[str, Any]], TypeAdapter],
    Dict[str, Any],
    Dict[str, FunctionMetadata],
]:
    """
    This function does the bulk of introspection, and also validates the user's capability.

    Basic logic:

    - Capabilities should implement functions which represent entrypoints
    - Each entrypoint should be annotated with @intersect_message() (this sets a hidden attribute)
    - Entrypoint functions should either have no parameters, or they should
      describe all their parameters in one BaseModel-derived class.
      (NOTE: maybe allow for some other input formats?)
    """

    function_map = {}
    schemas = {}
    channels = {}

    for name, method in _get_functions(capability, BASE_ATTR):
        docstring = method.__doc__
        signature = inspect.signature(method)
        method_params = tuple(signature.parameters.values())
        return_annotation = signature.return_annotation
        if len(method_params) == 0 or len(method_params) > 2:
            die(
                f"On capability '{capability.__name__}', function '{name.__name__}' should have 'self' and zero or one additional parameters"
            )

        # The schema format should be hard-coded and determined based on how Pydantic parses the schema.
        # See https://docs.pydantic.dev/latest/concepts/json_schema/ for that specification.
        channels[name] = {
            'publish': {
                'message': {
                    'schemaFormat': f'application/vnd.aai.asyncapi+json;version={ASYNCAPI_VERSION}',
                    'contentType': getattr(method, REQUEST_CONTENT),
                    'traits': {'$ref': '#/components/messageTraits/commonHeaders'},
                }
            },
            'subscribe': {
                'message': {
                    'schemaFormat': f'application/vnd.aai.asyncapi+json;version={ASYNCAPI_VERSION}',
                    'contentType': getattr(method, RESPONSE_CONTENT),
                    'traits': {'$ref': '#/components/messageTraits/commonHeaders'},
                }
            },
        }
        if docstring:
            docstring = docstring.strip()
            if docstring:
                channels[name]['publish']['description'] = docstring
                channels[name]['subscribe']['description'] = docstring

        # this block handles request params
        if len(method_params) == 2:
            parameter = method_params[1]
            annotation = parameter.annotation
            if annotation is inspect.Signature.empty:
                die(
                    f"On capability '{capability.__name__}', parameter '{parameter.name}' type annotation on function '{name.__name__}' missing. {SCHEMA_HELP_MSG}"
                )
            if annotation is None:
                function_cache_request_adapter = None
            else:
                try:
                    function_cache_request_adapter = TypeAdapter(annotation)
                    channels[name]['subscribe']['message']['payload'] = _merge_schema_definitions(
                        function_cache_request_adapter, schemas, annotation
                    )
                except PydanticUserError as e:
                    die(
                        f"On capability '{capability.__name__}', parameter '{parameter.name}' type annotation '{annotation.__name__}' on function '{name.__name__}' is invalid\n{e}"
                    )

        else:
            function_cache_request_adapter = None

        # this block handles response parameters
        if return_annotation is inspect.Signature.empty:
            die(
                f"On capability '{capability.__name__}', return type annotation on function '{name.__name__}' missing. {SCHEMA_HELP_MSG}"
            )
        if return_annotation is None:
            function_cache_response_adapter = None
        else:
            try:
                function_cache_response_adapter = TypeAdapter(return_annotation)
                channels[name]['publish']['message']['payload'] = _merge_schema_definitions(
                    function_cache_response_adapter, schemas, return_annotation
                )
            except PydanticUserError as e:
                die(
                    f"On capability '{capability.__name__}', return annotation '{return_annotation.__name__}' on function '{name.__name__}' cannot be used.\n{e}"
                )

        function_map[name] = FunctionMetadata(
            method,
            function_cache_request_adapter,
            function_cache_response_adapter,
        )

    if len(function_map) == 0:
        die(
            f"No entrypoints detected on class '{capability.__name__}'. Please annotate at least one entrypoint with '@intersect_message()' ."
        )

    return schemas, _status_fn_schema(capability, schemas), channels, function_map


def get_schema_and_functions_from_model(
    capability_type: Type,
    capability_name: HierarchyConfig,
    app_version: str,
) -> Tuple[Dict[str, Any], Dict[str, FunctionMetadata], Optional[str], TypeAdapter]:
    """
    This returns both the schema and the function mapping.

    This is meant for internal use - see "get_schema_from_model" for more comprehensive documentation.
    """
    (
        schemas,
        (status_fn_name, status_schema, status_type_adapter),
        channels,
        function_map,
    ) = _get_schemas_and_functions(capability_type)
    asyncapi_spec = {
        'asyncapi': ASYNCAPI_VERSION,
        'x-intersect-version': __version__,
        'info': {
            'title': capability_name.hierarchy_string('.'),
            'version': app_version,
        },
        # applies to how an incoming message payload will be parsed.
        # can be changed per channel
        'defaultContentType': 'application/json',
        'channels': channels,
        'components': {
            'schemas': schemas,
            'messageTraits': {
                # this is where we can define our message headers
                'commonHeaders': {
                    'headers': TypeAdapter(UserspaceMessageHeader).json_schema(
                        ref_template='#/components/messageTraits/commonHeaders/headers/$defs/{model}',
                        mode='serialization',
                    ),
                }
            },
        },
    }
    if capability_type.__doc__:
        trimmed_doc = capability_type.__doc__.strip()
        if trimmed_doc:
            asyncapi_spec['info']['description'] = trimmed_doc

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

    return asyncapi_spec, function_map, status_fn_name, status_type_adapter


def get_schema_from_model(
    capability_type: Type,
    capability_name: HierarchyConfig,
    app_version: str,
) -> Dict[str, Any]:
    """
    Params:
      - capability_type - the SDK user will provide the class of their capability handler, which generates the schema
      - capability_name - ideally, this could be scanned by the package name. Meant to be descriptive, i.e. "nionswift"
      - app_version - ideally, this could be parsed from the package.
      - status_fn: the function from your capability which retrieves its status

    The goal of this function is to be able to generate a complete schema
    matching the AsyncAPI spec 2.6.0 from a BaseModel class.

    SOME NOTES ABOUT THE SCHEMA
    - Inspired on AsyncAPI 2.6.0 (https://www.asyncapi.com/docs/reference/specification/v2.6.0)
      and OpenAPI 3.1.0 (https://swagger.io/specification/). Currently, the generated object
      tries to follow only AsyncAPI closely, though ideas from OpenAPI are used.
    - While all _required_ fields from the AsyncAPI spec are included, not all information is exposed.
    - There is currently no need to store information about the "servers" object, as this will be handled
      entirely via the SDK and its services. In the instance that multiple brokers are used,
      this field could potentially be useful to store information about the broker.
    - Not listing security mechanisms, as this gets handled by the SDK and its services.
    - No need to describe operation bindings for now. NOTE: this might be useful later on
      if we need to handle various protocols (i.e. http, mqtt, ws, nats, pulsar...)
    - Channel names just mimic the function names for now
    """
    schemas, _, _, _ = get_schema_and_functions_from_model(
        capability_type,
        capability_name,
        app_version,
    )
    return schemas

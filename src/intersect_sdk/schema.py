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
from typing import (
    Any,
    Dict,
    Optional,
    Tuple,
    Type,
)

from pydantic import TypeAdapter

from ._internal.function_metadata import FunctionMetadata
from ._internal.messages.userspace import UserspaceMessageHeader
from ._internal.schema import ASYNCAPI_VERSION, get_schemas_and_functions
from .config.shared import HierarchyConfig
from .version import __version__


def get_schema_and_functions_from_model(
    capability_type: Type,
    capability_name: HierarchyConfig,
    schema_version: str,
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
    ) = get_schemas_and_functions(capability_type)

    asyncapi_spec = {
        'asyncapi': ASYNCAPI_VERSION,
        'x-intersect-version': __version__,
        'info': {
            'title': capability_name.hierarchy_string('.'),
            'version': schema_version,
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
        asyncapi_spec['info']['description'] = inspect.cleandoc(capability_type.__doc__)

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
    schema_version: str,
) -> Dict[str, Any]:
    """
    Params:
      - capability_type - the SDK user will provide the class of their capability handler, which generates the schema
      - capability_name - ideally, this could be scanned by the package name. Meant to be descriptive, i.e. "nionswift"
      - schema_version - ideally, this could be parsed from the package.
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
        schema_version,
    )
    return schemas

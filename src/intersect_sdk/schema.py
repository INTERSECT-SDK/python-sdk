"""This module is responsible for generating the core interface definitions of any Service.

There are two things to generate:

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

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
)

from ._internal.schema import get_schema_and_functions_from_capability_implementations
from .capability.base import IntersectBaseCapabilityImplementation

if TYPE_CHECKING:
    from .config.shared import HierarchyConfig


def get_schema_from_capability_implementations(
    capability_types: list[type[IntersectBaseCapabilityImplementation]],
    hierarchy: HierarchyConfig,
) -> dict[str, Any]:
    """The goal of this function is to be able to generate a complete schema somewhat resembling the AsyncAPI spec 2.6.0 from a BaseModel class.

    The generated schema is currently not a complete replica of the AsyncAPI spec. See https://www.asyncapi.com/docs/reference/specification/v2.6.0 for the complete specification.
    Some key differences:
      - We utilize three custom fields: "capabilities", "events", and "status".
      - "capabilities" contains a dictionary: the keys of this dictionary are capability names. The values are dictionaries with the "description" property being a string which describes the capability,
        and a "channels" property which more closely follows the AsyncAPI specification of the top-level value "channels".
      - "events" is a key-value dictionary: the keys represent the event name, the values represent the associated schema of the event type. Events are currently shared across all capabilities.
      - "status" will have a value of the status schema - if no status has been defined, a null schema is used.

    Params:
      - capability_types - list of classes (not objects) of capabilities. We do not require capabilities to be instantiated here, in case the instantiation of a capability has external dependencies.
      - hierarchy - the hierarchy configuration. This is currently only reflected in the title of the global schema.
    """
    if not all(issubclass(cap, IntersectBaseCapabilityImplementation) for cap in capability_types):
        msg = 'get_schema_from_capability_implementations - not all provided values are valid capabilities (class must extend IntersectBaseCapabilityImplementation)'
        raise RuntimeError(msg)

    schemas, _, _, _, _, _ = get_schema_and_functions_from_capability_implementations(
        capability_types,
        hierarchy,
        set(),  # assume all data handlers are configured if user is just checking their schema
    )
    return schemas

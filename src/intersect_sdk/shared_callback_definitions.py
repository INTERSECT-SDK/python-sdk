"""Callback definitions shared between Services, Capabilities, and Clients."""

from typing import Any, Dict, List, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, TypeAlias

from .constants import SYSTEM_OF_SYSTEM_REGEX
from .core_definitions import IntersectDataHandler, IntersectMimeType

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


class IntersectDirectMessageParams(BaseModel):
    """These are the public-facing properties of a message which can be sent to another Service.

    This object can be used by Clients, and by Services if initiating a service-to-service request.
    """

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

    content_type: IntersectMimeType = IntersectMimeType.JSON
    """
    The IntersectMimeType of your message. You'll want this to match with the ContentType of the function from the schema.

    default: IntersectMimeType.JSON
    """

    data_handler: IntersectDataHandler = IntersectDataHandler.MESSAGE
    """
    The IntersectDataHandler you want to use (most people can just use IntersectDataHandler.MESSAGE here, unless your data is very large)

    default: IntersectDataHandler.MESSAGE
    """

    # pydantic config
    model_config = ConfigDict(revalidate_instances='always')

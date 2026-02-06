from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, NamedTuple

if TYPE_CHECKING:
    from pydantic import TypeAdapter

    from ..core_definitions import (
        IntersectDataHandler,
        IntersectEncryptionScheme,
        IntersectMimeType,
    )


class FunctionMetadata(NamedTuple):
    """Internal cache of public function metadata.

    NOTE: both this class and all properties in it should remain immutable after creation
    """

    capability: type
    """
    The type of the class that implements the target method.
    """
    request_adapter: TypeAdapter[Any] | Literal[0] | None
    """
    Type adapter for serializing and validating requests.

    Null if user did not specify a request parameter.
    0 if user did specify a request parameter, but Content-Type does not require a TypeAdapter.
    """
    response_adapter: TypeAdapter[Any] | Literal[0]
    """
    Type adapter for serializing and validating responses.
    0 if Content-Type does not require a TypeAdapter.
    """
    request_content_type: IntersectMimeType
    """
    Content-Type of the request value
    """
    response_content_type: IntersectMimeType
    """
    Content-Type of the response value
    """
    response_data_transfer_handler: IntersectDataHandler
    """
    How we intend on handling the response value
    """
    encryption_schemes: set[IntersectEncryptionScheme]
    """
    Supported encryption schemes
    """
    strict_validation: bool
    """
    Whether or not we're using lenient Pydantic validation (default, False) or strict
    """
    shutdown_keys: set[str]
    """
    keys which should cause the function to be skipped if set
    """

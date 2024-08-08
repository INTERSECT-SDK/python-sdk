from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, NamedTuple

if TYPE_CHECKING:
    from pydantic import TypeAdapter


class FunctionMetadata(NamedTuple):
    """Internal cache of public function metadata.

    NOTE: both this class and all properties in it should remain immutable after creation
    """

    capability: type
    """
    The type of the class that implements the target method.
    """
    method: Callable[[Any], Any]
    """
    The raw method of the function. The function itself is useless and should not be called,
    but will store user-defined attributes needed for internal handling of data.
    """
    request_adapter: TypeAdapter[Any] | None
    """
    Type adapter for serializing and validating requests. Should only be null if user did not specify a request parameter.
    """
    response_adapter: TypeAdapter[Any]
    """
    Type adapter for serializing and validating responses.
    """

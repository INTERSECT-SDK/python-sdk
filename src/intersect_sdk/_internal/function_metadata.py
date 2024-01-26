from typing import NamedTuple, Optional, Type

from pydantic import TypeAdapter


class FunctionMetadata(NamedTuple):
    """Internal cache of public function metadata.

    NOTE: both this class and all properties in it should remain immutable after creation
    """

    method: Type
    """
    The raw method of the function. The function itself is useless and should not be called,
    but will store user-defined attributes needed for internal handling of data.
    """
    request_adapter: Optional[TypeAdapter]
    """
    Type adapter for serializing and validating requests. Only null if request_type is also null.
    """
    response_adapter: Optional[TypeAdapter]
    """
    Type adapter for serializing and validating responses. Only null if response_type is also null.
    """

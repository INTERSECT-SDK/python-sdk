from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from pydantic import TypeAdapter


class StatusMetadata(NamedTuple):
    """Information we attach to status functions when running them in the Service loop."""

    capability_name: str
    function_name: str
    serializer: TypeAdapter[Any]

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from pydantic import TypeAdapter

    from ..core_definitions import IntersectDataHandler, IntersectMimeType
    from ..service_definitions import IntersectEventDefinition


class EventMetadata(NamedTuple):
    """Internal cache of metadata associated with an event.

    NOTE: both this class and all properties in it should remain immutable after creation
    """

    operations: set[str]
    """
    A hash set of operations which advertise this event
    """
    type: type
    """
    The actual type of the event
    """
    type_adapter: TypeAdapter[Any]
    """
    The type adapter used for deserializing and validating events
    """
    data_transfer_handler: IntersectDataHandler
    """
    The data transfer type
    """
    content_type: IntersectMimeType
    """
    The content type
    """


def definition_equals_metadata(
    definition: IntersectEventDefinition, metadata: EventMetadata
) -> bool:
    """Return true if 'definition' and 'metadata' have any overlap."""
    return (
        definition.event_type == metadata.type
        and definition.content_type == metadata.content_type
        and definition.data_handler == metadata.data_transfer_handler
    )

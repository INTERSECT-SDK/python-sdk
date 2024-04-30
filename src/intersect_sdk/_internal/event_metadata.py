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


def definition_metadata_differences(
    definition: IntersectEventDefinition, metadata: EventMetadata
) -> list[tuple[str, str, str]]:
    """Return a list of differences between 'definition' and 'metadata'.

    First tuple value = defintion key
    Second tuple value = second value
    Third tuple value = already cached value
    """
    differences = []
    if definition.event_type != metadata.type:
        differences.append(('event_type', str(definition.event_type), str(metadata.type)))
    if definition.content_type != metadata.content_type:
        differences.append(
            ('content_type', str(definition.content_type), str(metadata.content_type))
        )
    if definition.data_handler != metadata.data_transfer_handler:
        differences.append(
            ('data_handler', str(definition.data_handler), str(metadata.data_transfer_handler))
        )
    return differences

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
            (
                'content_type',
                f'{definition.content_type.__class__.__name__}.{definition.content_type.name}',
                f'{metadata.content_type.__class__.__name__}.{metadata.content_type.name}',
            )
        )
    if definition.data_handler != metadata.data_transfer_handler:
        differences.append(
            (
                'data_handler',
                f'{definition.data_handler.__class__.__name__}.{definition.data_handler.name}',
                f'{metadata.data_transfer_handler.__class__.__name__}.{metadata.data_transfer_handler.name}',
            )
        )
    return differences

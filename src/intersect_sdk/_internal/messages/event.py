"""This module contains core messaging definitions relating to INTERSECT events.

This module is internal-facing and should not be used directly by users.

Event messages are ALWAYS PRODUCED on the events channel.
Services should NEVER be CONSUMING messages on the events channel.
Clients/orchestrators are expected to consume these events themselves.
"""

import datetime
import uuid
from typing import Any, Union

from pydantic import AwareDatetime, Field, TypeAdapter
from typing_extensions import Annotated, TypedDict

from ...constants import SYSTEM_OF_SYSTEM_REGEX
from ...core_definitions import IntersectDataHandler, IntersectMimeType
from ...version import version_string
from ..data_plane.minio_utils import MinioPayload

# TODO - another property we should consider is an optional max_wait_time for events which are fired from functions.
# This would mostly be useful for clients/orchestrators that are waiting for a specific event.
# This should probably be configured on the schema level...


class EventMessageHeaders(TypedDict):
    """Matches the current header definition for INTERSECT messages.

    ALL messages should contain this header.
    """

    source: Annotated[
        str,
        Field(
            description='source of the message',
            pattern=SYSTEM_OF_SYSTEM_REGEX,
        ),
    ]
    """
    source of the message
    """

    created_at: Annotated[
        AwareDatetime,
        Field(
            description='the UTC timestamp of message creation',
        ),
    ]
    """
    created timestamp - should meet ISO-8601 format, always in UTC
    """

    sdk_version: Annotated[
        str,
        Field(
            pattern=r'^\d+\.\d+\.\d+$',
            description="SemVer string of SDK's version, used to check for compatibility",
        ),
    ]
    """
    The version of the SDK sending over the messages. Will be used to determine:
    - if two systems can communicate. SDKs will always be compatible if they share minor/bugfix versions.
      SDKs should be assumed NOT to be compatible if they don't share the major version.
    """

    data_handler: Annotated[
        IntersectDataHandler,
        Field(
            IntersectDataHandler.MESSAGE,
            description='Code signifying where data is stored.',
        ),
    ]
    """
    Code signifying where data is stored. If this value = IntersectDataHandler.MESSAGE (0), the data is directly in the payload.

    If the value equals anything else, the payload signifies the _pointer_ to the data. For example, if this value signifies MinIO
    usage, the payload would indicate the URI to where the data is stored on MinIO.
    """

    event_name: str
    """
    The name of an event. You can reasonably determine the structure of the message payload by parsing:

    1) the source of this message header
    2) this "name" property
    3) the service schema itself
    """


class EventMessage(TypedDict):
    messageId: uuid.UUID
    """
    ID of the message. (NOTE: this is defined here to conform to the AsyncAPI spec)
    """

    operationId: str
    """
    The name of the operation that was called when an event was emitted. These would map to the names of user functions.
    """

    headers: EventMessageHeaders
    """
    the headers of the message
    """

    payload: Union[bytes, MinioPayload]  # noqa: FA100 (Pydantic uses runtime annotations)
    """
    main payload of the message. Needs to match the schema format, including the content type.

    NOTE: The payload's contents will differ based on the data_handler property in the message header.
    """

    contentType: Annotated[IntersectMimeType, Field(IntersectMimeType.JSON)]
    """
    The content type to use when encoding/decoding a message's payload.
    The value MUST be a specific media type (e.g. application/json).
    When omitted, the value MUST be the one specified on the defaultContentType field.

    Note that if the data_handler type is anything other MESSAGE, the actual content-type of the message
    payload will depend on the data_handler type.
    """


def create_event_message(
    source: str,
    operation_id: str,
    content_type: IntersectMimeType,
    data_handler: IntersectDataHandler,
    event_name: str,
    payload: Any,
) -> EventMessage:
    """Payloads depend on the data handler."""
    return EventMessage(
        messageId=uuid.uuid4(),
        operationId=operation_id,
        contentType=content_type,
        payload=payload,
        headers=EventMessageHeaders(
            source=source,
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            sdk_version=version_string,
            event_name=event_name,
            data_handler=data_handler,
        ),
    )


EVENT_MESSAGE_ADAPTER = TypeAdapter(EventMessage)


def deserialize_and_validate_event_message(msg: bytes) -> EventMessage:
    """If the "msg" param is a valid userspace message, return the object.

    Raises Pydantic ValidationError if "msg" is not a valid userspace message
    """
    return EVENT_MESSAGE_ADAPTER.validate_json(msg, strict=True)

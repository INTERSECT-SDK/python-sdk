"""This module contains core messaging definitions relating to INTERSECT events.

This module is internal-facing and should not be used directly by users.

Event messages are ALWAYS PRODUCED on the events channel.
Services should NEVER be CONSUMING messages on the events channel.
Clients/orchestrators are expected to consume these events themselves.
"""

import datetime
import uuid
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, field_serializer

from ...constants import CAPABILITY_REGEX, SYSTEM_OF_SYSTEM_REGEX
from ...core_definitions import IntersectDataHandler
from ...version import version_string

# TODO - another property we should consider is an optional max_wait_time for events which are fired from functions.
# This would mostly be useful for clients/orchestrators that are waiting for a specific event.
# This should probably be configured on the schema level...


class EventMessageHeaders(BaseModel):
    """ALL event messages must include this header.

    We do not include the content type of the message in the header, it is handled separately.
    """

    message_id: uuid.UUID
    """
    ID of the message.
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

    capability_name: Annotated[
        str,
        Field(
            pattern=CAPABILITY_REGEX,
            description='The name of the capability which emitted the event originally.',
        ),
    ]
    """
    The name of the capability which emitted the event originally.
    """

    event_name: Annotated[
        str,
        Field(
            pattern=CAPABILITY_REGEX,
            description='The name of the event that was emitted, namespaced to the capability.',
        ),
    ]
    """
    The name of the event that was emitted. This is meaningless without the capability name.
    """

    # make sure all non-string fields are serialized into strings, even in Python code

    @field_serializer('message_id', mode='plain')
    def ser_uuid(self, uuid: uuid.UUID) -> str:
        return str(uuid)

    @field_serializer('created_at', mode='plain')
    def ser_datetime(self, dt: datetime.datetime) -> str:
        return dt.isoformat()

    @field_serializer('data_handler', mode='plain')
    def ser_enum(self, enum: IntersectDataHandler) -> str:
        return enum.value


def create_event_message_headers(
    source: str,
    capability_name: str,
    event_name: str,
    data_handler: IntersectDataHandler,
) -> dict[str, str]:
    """Generate raw headers and write them into a generic data structure which can be handled by any broker protocol."""
    return EventMessageHeaders(
        source=source,
        message_id=uuid.uuid4(),
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        sdk_version=version_string,
        capability_name=capability_name,
        event_name=event_name,
        data_handler=data_handler,
    ).model_dump(by_alias=True)


def validate_event_message_headers(raw_headers: dict[str, str]) -> EventMessageHeaders:
    """Validate raw headers and return the object.

    Raises:
      pydantic.ValidationError - if the headers were missing any essential information
    """
    return EventMessageHeaders(**raw_headers)  # type: ignore[arg-type]

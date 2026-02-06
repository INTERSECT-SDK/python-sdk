"""This module contains core messaging definitions relating to user-defined functions.

This module is internal-facing and should not be used directly by users.

Services have two associated channels which handle userspace messages: their request channel
and their response channel. Services always CONSUME messages from these channels, but never PRODUCE messages
on these channels. (A message is always sent in the receiver's namespace).

The response channel is how the service handles external requests, the request channel is used when this service itself
needs to make external requests through INTERSECT.

Services should ALWAYS be CONSUMING from their userspace channel.
They should NEVER be PRODUCING messages on their userspace channel.

Clients should be CONSUMING from their userspace channel, but should only get messages
from services they explicitly messaged.
"""

import datetime
import uuid
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, field_serializer

from ...constants import SYSTEM_OF_SYSTEM_REGEX
from ...core_definitions import (
    IntersectDataHandler,
)
from ...version import version_string


class UserspaceMessageHeaders(BaseModel):
    """ALL request/response/command messages must contain this header.

    We do not include the content type of the message in the header, it is handled separately.
    """

    message_id: Annotated[uuid.UUID, Field(description='Unique message ID')]
    """
    ID of the message.
    """

    campaign_id: Annotated[uuid.UUID, Field(description='ID associated with a campaign')]
    """
    ID of the campaign. For Clients, this should be set once per run, and then not changed. For orchestrators, this is associated with a campaign.
    """

    request_id: Annotated[
        uuid.UUID,
        Field(
            description='ID associated with a specific request message and response message sequence'
        ),
    ]
    """
    ID of the request. A Client/orchestrator generates this ID for each request message it sends, and the Service generates a response message with this ID.
    """

    source: Annotated[
        str, Field(description='source of the message', pattern=SYSTEM_OF_SYSTEM_REGEX)
    ]
    """
    source of the message
    """

    destination: Annotated[
        str, Field(description='destination of the message', pattern=SYSTEM_OF_SYSTEM_REGEX)
    ]
    """
    destination of the message
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

    operation_id: Annotated[
        str,
        Field(
            description='Name of capability and operation we want to call, in the format ${CAPABILITY_NAME}.${FUNCTION_NAME}'
        ),
    ]
    """
    The name of the operation we want to call. For Services, this indicates the operation which will be called; for Clients, this is the operation which was called.

    This maps to the format ${CAPABILITY_NAME}.${FUNCTION_NAME} .
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

    has_error: Annotated[
        bool,
        Field(
            False,
            description='If this value is True, the payload will contain the error message (a string)',
        ),
    ]
    """
    If this flag is set to True, the payload will contain the error message (always a string).

    This should only be set to "True" on return messages sent by services - NEVER clients.
    """

    # make sure all non-string fields are serialized into strings, even in Python code

    @field_serializer('message_id', 'request_id', 'campaign_id', mode='plain')
    def ser_uuid(self, uuid: uuid.UUID) -> str:
        return str(uuid)

    @field_serializer('created_at', mode='plain')
    def ser_datetime(self, dt: datetime.datetime) -> str:
        return dt.isoformat()

    @field_serializer('has_error', mode='plain')
    def ser_boolean(self, boolean: bool) -> str:
        return str(boolean).lower()

    @field_serializer('data_handler', mode='plain')
    def ser_enum(self, enum: IntersectDataHandler) -> str:
        return enum.value


def create_userspace_message_headers(
    source: str,
    destination: str,
    operation_id: str,
    data_handler: IntersectDataHandler,
    campaign_id: uuid.UUID,
    request_id: uuid.UUID,
    has_error: bool = False,
) -> dict[str, str]:
    """Generate raw headers and write them into a generic data structure which can be handled by any broker protocol."""
    return UserspaceMessageHeaders(
        message_id=uuid.uuid4(),
        campaign_id=campaign_id,
        request_id=request_id,
        source=source,
        destination=destination,
        sdk_version=version_string,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        operation_id=operation_id,
        data_handler=data_handler,
        has_error=has_error,
    ).model_dump(by_alias=True)


def validate_userspace_message_headers(raw_headers: dict[str, str]) -> UserspaceMessageHeaders:
    """Validate raw headers and return the object.

    Raises:
      pydantic.ValidationError - if the headers were missing any essential information
    """
    return UserspaceMessageHeaders(**raw_headers)  # type: ignore[arg-type]

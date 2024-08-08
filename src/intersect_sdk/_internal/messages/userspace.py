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

from __future__ import annotations

import datetime
import uuid
from typing import Any, Union

from pydantic import AwareDatetime, Field, TypeAdapter
from typing_extensions import Annotated, TypedDict

from ...constants import SYSTEM_OF_SYSTEM_REGEX  # noqa: TCH001 (this is runtime checked)
from ...core_definitions import (  # noqa: TCH001 (this is runtime checked)
    IntersectDataHandler,
    IntersectMimeType,
)
from ...version import version_string
from ..data_plane.minio_utils import MinioPayload  # noqa: TCH001 (this is runtime checked)


class UserspaceMessageHeader(TypedDict):
    """Matches the current header definition for INTERSECT messages.

    ALL messages should contain this header.
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


class UserspaceMessage(TypedDict):
    """Core definition of a message.

    The structure of this class is meant to somewhat closely mirror the AsyncAPI definition of a message:
    https://www.asyncapi.com/docs/reference/specification/v2.6.0#messageObject
    """

    messageId: uuid.UUID
    """
    ID of the message. (NOTE: this is defined here to conform to the AsyncAPI spec)
    """

    operationId: str
    """
    The name of the operation we want to call. These would map to the names of user functions.
    """

    headers: UserspaceMessageHeader
    """
    the headers of the message
    """

    payload: Union[bytes, MinioPayload]  # noqa: UP007 (Pydantic uses runtime annotations)
    """
    main payload of the message. Needs to match the schema format, including the content type.

    NOTE: The payload's contents will differ based on the data_handler property in the message header.
    NOTE: If "has_error" flag in the message headers is set to "True", the payload will instead contain an error string.
    """

    contentType: Annotated[IntersectMimeType, Field(IntersectMimeType.JSON)]
    """
    The content type to use when encoding/decoding a message's payload.
    The value MUST be a specific media type (e.g. application/json).
    When omitted, the value MUST be the one specified on the defaultContentType field.

    Note that if the data_handler type is anything other MESSAGE, the actual content-type of the message
    payload will depend on the data_handler type.
    """


def create_userspace_message(
    source: str,
    destination: str,
    operation_id: str,
    content_type: IntersectMimeType,
    data_handler: IntersectDataHandler,
    payload: Any,
    message_id: uuid.UUID | None = None,
    has_error: bool = False,
) -> UserspaceMessage:
    """Payloads depend on the data_handler and has_error."""
    msg_id = message_id if message_id else uuid.uuid4()
    return UserspaceMessage(
        messageId=msg_id,
        operationId=operation_id,
        contentType=content_type,
        payload=payload,
        headers=UserspaceMessageHeader(
            source=source,
            destination=destination,
            sdk_version=version_string,
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            data_handler=data_handler,
            has_error=has_error,
        ),
    )


USERSPACE_MESSAGE_ADAPTER = TypeAdapter(UserspaceMessage)


def deserialize_and_validate_userspace_message(msg: bytes) -> UserspaceMessage:
    """If the "msg" param is a valid userspace message, return the object.

    Raises Pydantic ValidationError if "msg" is not a valid userspace message
    """
    return USERSPACE_MESSAGE_ADAPTER.validate_json(msg, strict=True)

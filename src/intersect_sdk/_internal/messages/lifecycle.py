"""This module contains core messaging definitions relating to INTERSECT lifecycle actions.

This module is internal-facing and should not be used directly by users.

Lifecycle messages are ALWAYS PRODUCED on the lifecycle channel.
Services should NEVER be CONSUMING messages on the lifecycle channel.
(consumption is for INTERSECT core services only).
"""

import datetime
import uuid
from enum import IntEnum
from typing import Any, Literal

from pydantic import AwareDatetime, Field, TypeAdapter
from typing_extensions import Annotated, TypedDict

from ...constants import SYSTEM_OF_SYSTEM_REGEX
from ...version import version_string


class LifecycleType(IntEnum):
    """Lifecycle code which needs to be included in every message sent.

    The lifecycle code is also what determines the structure of the payload.
    """

    STARTUP = 0
    """
    Message sent on startup. Includes the schema in the payload.
    """
    SHUTDOWN = 1
    """
    Message sent on shutdown. Can send a reason for shutdown in the payload.
    """
    POLLING = 2
    """
    Message periodically sent out to indicate liveliness.
    Failure to send a lifecycle message indicates unhealthy service.
    A message with a POLLING enumeration also implies that the status has not been updated.

    Includes the schema and the current status in the payload ({'schema': schema_str, 'status': current_status})
    """
    STATUS_UPDATE = 3
    """
    Message sent out to explicitly indicate there was a status update.
    Status updates are checked each time a user function is called and during the polling interval.

    Includes the schema and the new status in the payload ({'schema': schema_str, 'status': current_status})
    """
    FUNCTIONS_ALLOWED = 4
    """
    Send out a list of functions now allowed in the payload
    """
    FUNCTIONS_BLOCKED = 5
    """
    Send out a list of functions now blocked in the payload
    """


class LifecycleMessageHeaders(TypedDict):
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

    destination: Annotated[
        str,
        Field(
            description='destination of the message',
            pattern=SYSTEM_OF_SYSTEM_REGEX,
        ),
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

    lifecycle_type: LifecycleType
    """
    The integer code of the lifecycle message being sent/received.
    """


class LifecycleMessage(TypedDict):
    messageId: uuid.UUID
    """
    ID of the message. (NOTE: this is defined here to conform to the AsyncAPI spec)
    """

    headers: LifecycleMessageHeaders
    """
    the headers of the message
    """

    payload: Any
    """
    main payload of the message.

    NOTE: The payload's contents will differ based on the lifecycle_type property in the message header.
    """

    contentType: Annotated[Literal['application/json'], Field('application/json')]
    """
    The content type to use when encoding/decoding a message's payload.

    NOTE: ContentType is provided to somewhat match the AsyncAPI spec, but this value must ALWAYS be
    application/json , as a lifecycle message's payload should ALWAYS be represented in JSON.
    """


def create_lifecycle_message(
    source: str,
    destination: str,
    lifecycle_type: LifecycleType,
    payload: Any,
) -> LifecycleMessage:
    """The contents of the payload should vary based on the lifecycle type."""
    return LifecycleMessage(
        messageId=uuid.uuid4(),
        headers=LifecycleMessageHeaders(
            source=source,
            destination=destination,
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            sdk_version=version_string,
            lifecycle_type=lifecycle_type,
        ),
        payload=payload,
        contentType='application/json',
    )


LIFECYCLE_MESSAGE_ADAPTER = TypeAdapter(LifecycleMessage)


def deserialize_and_validate_lifecycle_message(msg: bytes) -> LifecycleMessage:
    """If the "msg" param is a valid userspace message, return the object.

    Raises Pydantic ValidationError if "msg" is not a valid userspace message
    """
    return LIFECYCLE_MESSAGE_ADAPTER.validate_json(msg, strict=True)

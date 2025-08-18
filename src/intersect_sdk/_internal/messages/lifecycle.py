"""This module contains core messaging definitions relating to INTERSECT lifecycle actions.

This module is internal-facing and should not be used directly by users.

Lifecycle messages are ALWAYS PRODUCED on the lifecycle channel.
Services should NEVER be CONSUMING messages on the lifecycle channel.
(consumption is for INTERSECT core services only).
"""

import datetime
import uuid
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, field_serializer

from ...constants import SYSTEM_OF_SYSTEM_REGEX
from ...version import version_string

LifecycleType = Literal[
    'LCT_STARTUP',
    'LCT_SHUTDOWN',
    'LCT_POLLING',
    'LCT_FUNCTIONS_ALLOWED',
    'LCT_FUNCTIONS_BLOCKED',
]


class LifecycleMessageHeaders(BaseModel):
    """ALL lifecycle messages must include this header.

    We do not include the content type of the message in the header, it is handled separately.

    A special note about lifecycle messages is that their content type must ALWAYS be "application/json".
    """

    message_id: Annotated[uuid.UUID, Field()]
    """UUID of the message."""

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

    lifecycle_type: LifecycleType
    """
    The integer code of the lifecycle message being sent/received.
    """

    # make sure all non-string fields are serialized into strings, even in Python code

    @field_serializer('message_id', mode='plain')
    def ser_uuid(self, uuid: uuid.UUID) -> str:
        return str(uuid)

    @field_serializer('created_at', mode='plain')
    def ser_datetime(self, dt: datetime.datetime) -> str:
        return dt.isoformat()


def create_lifecycle_message_headers(
    source: str,
    lifecycle_type: LifecycleType,
) -> dict[str, str]:
    """Generate raw headers and write them into a generic data structure which can be handled by any broker protocol.

    The contents of the payload should vary based on the lifecycle type.
    """
    return LifecycleMessageHeaders(
        source=source,
        message_id=uuid.uuid4(),
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        sdk_version=version_string,
        lifecycle_type=lifecycle_type,
    ).model_dump(by_alias=True)


def validate_lifecycle_message_headers(raw_headers: dict[str, str]) -> LifecycleMessageHeaders:
    return LifecycleMessageHeaders(**raw_headers)  # type: ignore[arg-type]

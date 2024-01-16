"""
This module contains core messaging definitions relating to user-defined functions.
This module is internal-facing and should not be used directly by users.

Services should ALWAYS be CONSUMING from their userspace channel.
They should NEVER be PRODUCING messages on their userspace channel.
"""

import datetime
from typing import Any
from uuid import uuid4

from pydantic import Field, TypeAdapter
from typing_extensions import Annotated, TypedDict

from ...annotations import IntersectDataHandler, IntersectMimeType
from ...version import __version__


class UserspaceMessageHeader(TypedDict):
    """
    Matches the current header definition for INTERSECT messages.

    ALL messages should contain this header.
    """

    source: Annotated[str, Field(description='source of the message')]
    """
    source of the message
    """

    destination: Annotated[str, Field(description='destination of the message')]
    """
    destination of the message
    """

    created_at: Annotated[
        str,
        Field(
            description='the UTC timestamp of message creation',
        ),
    ]
    """
    created timestamp - should meet ISO-8601 format, always in UTC
    """

    service_version: Annotated[
        str,
        Field(
            pattern=r'^\d+\.\d+\.\d+$',
            description="SemVer string of service's version, used to check for compatibility",
        ),
    ]
    """
    The version of the SERVICE sending over the messages. Will be used to determine:
    - When a campaign is created with an older version, and the version is updated,
      parsing the version will determine if the old campaign can still be executed.
      Ideally, you'd use semantic versioning, and only bump the major version
      on backwards incompatibilities.
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


class UserspaceMessage(TypedDict):
    """
    Core definition of a message.

    The structure of this class is meant to somewhat closely mirror the AsyncAPI definition of a message:
    https://www.asyncapi.com/docs/reference/specification/v2.6.0#messageObject
    """

    messageId: Annotated[str, Field(default_factory=lambda: str(uuid4()))]
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

    payload: Any
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


def create_userspace_message(
    source: str,
    destination: str,
    service_version: str,
    operation_id: str,
    content_type: IntersectMimeType,
    data_handler: IntersectDataHandler,
    payload: Any,
) -> UserspaceMessage:
    return UserspaceMessage(
        messageId=str(uuid4()),
        operationId=operation_id,
        contentType=content_type,
        payload=payload,
        headers=UserspaceMessageHeader(
            source=source,
            destination=destination,
            service_version=service_version,
            sdk_version=__version__,
            created_at=f'{datetime.datetime.utcnow().isoformat()}Z',
            data_handler=data_handler,
        ),
    )


USERSPACE_MESSAGE_ADAPTER = TypeAdapter(UserspaceMessage)


def deserialize_and_validate_userspace_message(msg: bytes) -> UserspaceMessage:
    """
    If the "msg" param is a valid userspace message, return the object

    Raises Pydantic ValidationError if "msg" is not a valid userspace message
    """
    return USERSPACE_MESSAGE_ADAPTER.validate_json(msg, strict=True)

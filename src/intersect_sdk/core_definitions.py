"""Core enumerations and structures used throughout INTERSECT, for both client and service."""

from enum import IntEnum

from pydantic import Field
from typing_extensions import Annotated


class IntersectDataHandler(IntEnum):
    """What data transfer type do you want to use for handling the request/response?

    Default: MESSAGE
    """

    MESSAGE = 0
    MINIO = 1


IntersectMimeType = Annotated[str, Field(pattern=r'\w+/[-+.\w]+')]
"""
Special typing which represents a "Content-Type" value (i.e. `application/json`).

The value should be a MIME type; references can be found at:

- https://www.iana.org/assignments/media-types/media-types.xhtml

- https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types

These values are used to help map an output (or a part of an output) from an arbitrary microservice to an input (or a part of an input) of another arbitrary microservice.

In general, mime types follow one of two rules:
- Complex types (types which cannot be represented as a sequence of bytes) MUST be represented by a Content-Type of 'application/json' (this is default).
  If a complex type has binary data in a field, this field MUST be Base64 encoded.
  You can mark the type with either 'pydantic.Base64Bytes', or if you need the value to be URL safe, 'pydantic.Base64UrlBytes'. You MUST also specify the "contentType" property, like this:
    field: Annotated[pydantic.Base64Bytes, pydantic.Field(json_schema_extra={"contentType": "image/png"})]

  INTERSECT is able to handle serialization/deserialization of 'application/json' types for you, though note that you will need to verify binary data (incoming and outgoing) yourself. INTERSECT will handle the Base64 encoding/decoding, though.
- If your Content-Type value is ANYTHING ELSE, you MUST mark it as "bytes" . In this instance, INTERSECT will not base64-encode or base64-decode the value.
"""

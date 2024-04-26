"""Core enumerations and structures used throughout INTERSECT, for both client and service."""

from enum import Enum, IntEnum


class IntersectDataHandler(IntEnum):
    """What data transfer type do you want to use for handling the request/response?

    Default: MESSAGE
    """

    MESSAGE = 0
    MINIO = 1


class IntersectMimeType(Enum):
    """Roughly corresponds to "Content-Type" values, but enforce standardization of values.

    Default: JSON

    The value should be a MIME type; references can be found at:

    - https://www.iana.org/assignments/media-types/media-types.xhtml

    - https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types

    JSON is acceptable for any file which contains non-binary data.

    BINARY is acceptable for any file which contains binary data and can reasonably be handled as application/octet-string.

    This list is not exhaustive and should be regularly updated. If this list is missing a MIME type you would like to use, please contact the developers or open an issue.
    """

    JSON = 'application/json'
    STRING = 'text/plain'
    BINARY = 'application/octet-string'
    HDF5 = 'application/x-hdf5'

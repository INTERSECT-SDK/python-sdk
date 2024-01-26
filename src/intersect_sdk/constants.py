"""These are miscellaneous constants used in INTERSECT which SDK users may obtain value from knowing about."""

SYSTEM_OF_SYSTEM_REGEX = r'([-a-z0-9]+\.)*[-a-z0-9]'
"""
This is the regex used as a representation of a source/destination.
This is only needed externally if you are building a client, services can ignore this.

NOTE: for future compatibility reasons, we are NOT specifying the number of "parts" (separated by a '.') in this regex.
"""

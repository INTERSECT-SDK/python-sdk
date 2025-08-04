"""These are miscellaneous constants used in INTERSECT which SDK users may obtain value from knowing about."""

SYSTEM_OF_SYSTEM_REGEX = r'^[a-z0-9][-a-z0-9.]*[-a-z0-9]$'
"""
This is the regex used as a representation of a source/destination.
This is only needed externally if you are building a client, services can ignore this.

NOTE: for future compatibility reasons, we are NOT specifying the number of "parts" (separated by a '.') in this regex. All that matters is that you don't start or end with a period, or start with a hyphen.
"""

# see the internal schema file for full validation details
CAPABILITY_REGEX = r'^[a-zA-Z0-9]\w*$'
"""
This is the regex used for representing capabilities and event keys. Capabilities should start with an alphanumeric character, and not be longer than 255 characters.

This regex applies to namespacing local to a Service, so does not have to be unique across the ecosystem.
"""

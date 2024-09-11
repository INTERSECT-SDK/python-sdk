"""Basic INTERSECT-SDK version information.

These values are often used programmatically by the SDK, but can be used by application developers as well.
"""

from __future__ import annotations

from ._internal.version import strip_version_metadata

# may include build metadata
__version__ = '0.8.0'

version_string = strip_version_metadata(__version__)
"""
Version string in the format <MAJOR>.<MINOR>.<DEBUG> . Follows semantic versioning rules, strips out additional build metadata.
"""

version_info: tuple[int, int, int] = tuple([int(x) for x in version_string.split('.')])  # type: ignore[assignment]
"""
Integer tuple in the format <MAJOR>,<MINOR>,<DEBUG> . Follows semantic versioning rules.
"""

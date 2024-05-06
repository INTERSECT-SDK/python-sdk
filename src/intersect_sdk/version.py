"""Basic INTERSECT-SDK version information.

These values are often used programmatically by the SDK, but can be used by application developers as well.
"""

from __future__ import annotations

__version__ = '0.6.1'
"""
Version string in the format <MAJOR>.<MINOR>.<DEBUG> . Follows semantic versioning rules.
"""
version_info: tuple[int, int, int] = tuple([int(x) for x in __version__.split('.')])  # type: ignore[assignment]
"""
Integer tuple in the format <MAJOR>,<MINOR>,<DEBUG> . Follows semantic versioning rules.
"""

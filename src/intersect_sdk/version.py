"""Basic INTERSECT-SDK version information.

These values are often used programmatically by the SDK, but can be used by application developers as well.
"""

from importlib.metadata import version

# may include build metadata
__version__ = version('intersect-sdk')

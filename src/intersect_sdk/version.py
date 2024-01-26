"""Basic INTERSECT-SDK version information.

These values are often used programmatically by the SDK, but can be used by application developers as well.
"""
__version__ = '0.5.0'
"""
Version string in the format <MAJOR>.<MINOR>.<DEBUG> . Follows semantic versioning rules.
"""
version_info = tuple([int(x) for x in __version__.split('.')])
"""
Integer tuple in the format <MAJOR>,<MINOR>,<DEBUG> . Follows semantic versioning rules.
"""

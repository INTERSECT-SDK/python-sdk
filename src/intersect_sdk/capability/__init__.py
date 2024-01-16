"""
This module contains implementations of core INTERSECT-SDK capabilities.

Note that many applications shouldn't need to implement most capabilities directly.
There are various INTERSECT capabilities packages which can provide these interfaces for you.
The benefit of using pre-existing INTERSECT capabilities over using your own is that it's easier
for campaign authors and automated workflows to discover your instrument.
"""

from .core import IntersectCapability, IntersectCoreCapability

__all__ = [
    'IntersectCapability',
    'IntersectCoreCapability',
]

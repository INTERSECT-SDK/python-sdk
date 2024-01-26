"""This module contains implementations of core INTERSECT-SDK capabilities.

Note that application developers shouldn't need to concern themselves with this package, but should instead look into various capabilities packages instead.
There are various INTERSECT capabilities packages which can provide these interfaces for you.
The benefit of using pre-existing INTERSECT capabilities over using your own is that it's easier
for campaign authors and automated workflows to discover your instrument.
"""

from .core import IntersectCapability, IntersectCoreCapability

__all__ = [
    'IntersectCapability',
    'IntersectCoreCapability',
]

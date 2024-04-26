"""This module contains implementations of core INTERSECT-SDK capabilities.

The most important submodule from this package is the "base" module, which contains core capability definitions.

This package will also be important for INTERSECT capability authors, which can provide standardized interfaces.
The benefit of using pre-existing INTERSECT capabilities over using your own is that it's easier
for campaign authors and automated workflows to discover your instrument.
"""

from .base import IntersectBaseCapabilityImplementation

__all__ = [
    'IntersectBaseCapabilityImplementation',
]

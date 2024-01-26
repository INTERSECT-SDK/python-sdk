"""Core definitions for capabilities, to be extended in capability libraries."""


class IntersectCapability:
    """Base class for all capabilities.

    This is just a marker class, but EVERY capability will need to extend this class.

    This is mostly used for capability library authors; adapter implementions should NOT
    use this class or need to worry about implementing this class.
    """


class IntersectCoreCapability(IntersectCapability):
    """ALL services must implement either this capability, or a capability which extends from this capability.

    Library authors would be advised not to extend from this class, but from IntersectCapability instead.
    """

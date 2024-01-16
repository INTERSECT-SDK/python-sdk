class IntersectException(Exception):
    """
    generic marker for INTERSECT-specific exceptions
    """


class IntersectApplicationException(IntersectException):
    """
    thrown if:

    1) user application logic throws _any_ kind of Exception, or
    2) if input parameters do not validate against schema.

    It doesn't make much sense to separate the two, as JSON schema is NOT a complete prescription for input validation.

    This exception should strictly be used for control flow - it should NEVER be a fatal exception
    """


class IntersectInvalidBrokerException(IntersectException):
    """Exception when invalid broker backend used."""

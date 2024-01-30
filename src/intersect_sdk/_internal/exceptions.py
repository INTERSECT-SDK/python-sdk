class IntersectError(Exception):
    """Generic marker for INTERSECT-specific exceptions."""


class IntersectApplicationError(IntersectError):
    """This is a special IntersectException, thrown if user application logic throws ANY kind of Exception.

    In general, validation should be expressed through JSON schema as much as possible; however, JSON schema is NOT a complete prescription for input validation.
    When this exception is thrown, however, we do not leak any exception information in the error message. On the other hand, if the input fails
    JSON schema validation, Pydantic will throw a specific ValidationError, and that exception information will deliberately be exposed in the error message.

    This exception should strictly be used for control flow - it should NEVER be a fatal exception
    """


class IntersectInvalidBrokerError(IntersectError):
    """Exception when invalid broker backend used."""

class IntersectException(Exception):
    """Raised when an error occurs with the INTERSECT protocol."""

    pass


class IntersectWarning(Exception):
    """Raised when a potential problem occurs with the INTERSECT protocol."""

    pass


class IntersectConfigParseException(IntersectException):
    """
    Exceptions raised relating to the creation of an INTERSECT configuration object.
    You will probably want to stop the program if this exception happens, instead of recovering.

    PARAMS:
        returnCode: exit code (for precise exit codes other than 1, see:
    https://www.freebsd.org/cgi/man.cgi?query=sysexits&apropos=0&sektion=0&manpath=FreeBSD+4.3-RELEASE&format=html)
        message: error message
    """

    def __init__(self, returnCode=1, message="Error parsing INTERSECT configuration"):
        self.returnCode = returnCode
        self.message = message

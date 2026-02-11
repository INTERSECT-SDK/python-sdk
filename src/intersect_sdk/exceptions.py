"""Public exceptions API."""

from ._internal.exceptions import IntersectError


class IntersectCapabilityError(IntersectError):
    """This is a marker for a special kind of Capability Exception. WARNING: USE THIS WITH CARE.

    When the SDK catches an Exception from Capability code, it has to decide whether to send information about the Exception in the message, or a generic "Application raised Exception" message.

    The SDK will NOT propagate uncaught exceptions from Capabilities.
    In many cases, these exceptions are accidentally thrown, and could leak sensitive information.
    The one exception to this are Pydantic's ValidationErrors, which should always be happening due to bad user input (so letting the user know about their invalid user input is important).

    This Exception provides a way for the SDK to know that your Capability explicitly threw this Exception, since nothing else in the SDK will throw it.
    If you explicitly throw an IntersectCapabilityError and attach a message to it, the SDK will send this message out publicly.
    This can be useful for diagnostic purposes, or you may just want to catch an error and fully inform clients about it.

    For example, the following code will send the generic "Service domain logic threw exception" message through INTERSECT (this is an uncaught ZeroDivisionError):

    ```
    @intersect_message
    def call_division(self) -> float:
      return 7 / 0
    ```

    The following code will send: "Service domain logic threw explicit exception: division by zero"

    ```
    @intersect_message
    def call_division(self) -> float:
      try:
        return 7 / 0
      except ZeroDivisionError as e:
        raise IntersectCapabilityError(str(e))
    ```

    Note that this Exception is only useful for `@intersect_message` annotated functions, as Clients are expecting a response.
    It is pointless to throw this exception in events, because no message will get sent out if event code errors out.
    """

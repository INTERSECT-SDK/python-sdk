"""Basic Capability definitions."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import final

from .._internal.constants import BASE_EVENT_ATTR, BASE_RESPONSE_ATTR, BASE_STATUS_ATTR
from .._internal.logger import logger

if TYPE_CHECKING:
    from uuid import UUID

    from .._internal.interfaces import IntersectEventObserver
    from ..service_callback_definitions import (
        INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
    )
    from ..shared_callback_definitions import (
        IntersectDirectMessageParams,
    )


class IntersectBaseCapabilityImplementation:
    """Base class for all capabilities.

    EVERY capability implementation will need to extend this class. Additionally, if you redefine the constructor,
    you MUST call `super.__init__()` .
    """

    intersect_sdk_capability_name: ClassVar[str] = ''
    """The advertised name of your capability, as provided by the extension of this class.

    You MUST override this value per class and set it as a string - it's ideal to do so on the class itself for static analysis purposes,
    though as long as this variable has been set before the capability is added to the Service,
    everything should work fine.

    Each capability within a Service MUST have a unique capability name.
    This value should not be modified once the capability has been added to the Service.
    This value should ONLY contain alphanumeric characters, hyphens, and underscores.
    """

    def __init__(self) -> None:
        """This constructor just sets up observers.

        NOTE: If you write your own constructor, you MUST call `super.__init__()` inside of it. The Service will throw an error if you don't.
        """
        self.__intersect_sdk_observers__: list[IntersectEventObserver] = []
        """
        INTERNAL USE ONLY.

        These are observers that the capability can emit events to.
        """

    def __init_subclass__(cls) -> None:
        """This prevents users from overriding a few key functions.

        General rule of thumb is that any function which starts with `intersect_sdk_` is a protected namespace for defining
        the INTERSECT-SDK public API between a capability and its observers.
        """
        if (
            cls._intersect_sdk_register_observer
            is not IntersectBaseCapabilityImplementation._intersect_sdk_register_observer
            or cls.intersect_sdk_emit_event
            is not IntersectBaseCapabilityImplementation.intersect_sdk_emit_event
            or cls.intersect_sdk_call_service
            is not IntersectBaseCapabilityImplementation.intersect_sdk_call_service
        ):
            msg = f"{cls.__name__}: Attempted to override a reserved INTERSECT-SDK function (don't start your function names with '_intersect_sdk_' or 'intersect_sdk_')"
            raise RuntimeError(msg)

    @final
    def _intersect_sdk_register_observer(self, observer: IntersectEventObserver) -> None:
        """INTERNAL USE ONLY."""
        # observer must have a specific callable function
        self.__intersect_sdk_observers__.append(observer)

    @final
    def intersect_sdk_emit_event(self, event_name: str, event_value: Any) -> None:
        """Emits an event into the INTERSECT system.

        If you are emitting an event inside either an @intersect_message decorated function, or ANY FUNCTION called
        internally from an @intersect_message decorated function, you MUST register the event on the @intersect_message.
        If you're emitting an event from an internal function eventually called from multiple @intersect_message functions,
        you must register the event on ALL @intersect_message functions which call this event-emitting function.

        You may also emit an event from any function annotated with @intersect_event, or called after it, but you MUST
        register the event on the @intersect_event decorator. The @intersect_event annotation will be IGNORED if you place it
        after an @intersect_message annotation; its intended use is for threaded functions you start from the capability.

        Do NOT call this function from:
          - any function called from an @intersect_status decorated function
          - outside of the capability class (for example: capability_instance.intersect_sdk_emit_event(...) will not work). Create a function in the capability, decorate it with @intersect_event, and call that function.

        params:
          event_name: the type of event you are emitting. Note that you must advertise the event in your "entrypoint" function
          event_value: the value associated with the event. Note that this value must be accurate to its typing annotation.
        """
        annotated_operation = None
        # we iterate over the stack in REVERSE for two reasons:
        # 1) we want to find the FIRST function (the "entrypoint") which is annotated.
        # 2) in case the user has a large call stack
        # TODO - this is an O(n) operation in a hot loop, try to optimize this later! Responses should have a constant based off library code, events we could potentially restrict.
        for frame_info in reversed(inspect.stack()):
            try:
                capability_function = getattr(self, frame_info.function)
                if hasattr(capability_function, BASE_STATUS_ATTR):
                    logger.error(
                        f'Cannot emit an event from @intersect_status function {frame_info.function}'
                    )
                    # we won't throw an exception here because users could potentially catch it
                    # (and don't force failure because this is in a hot loop)
                    # just decline to emit the event and continue on normally
                    return
                if hasattr(capability_function, BASE_EVENT_ATTR) or hasattr(
                    capability_function, BASE_RESPONSE_ATTR
                ):
                    annotated_operation = frame_info.function
                    break
            except AttributeError:
                pass
        if annotated_operation is None:
            logger.error(
                f"You did not register event '{event_name}' on an @intersect_message or @intersect_event function."
            )
            return
        for observer in self.__intersect_sdk_observers__:
            observer._on_observe_event(event_name, event_value, annotated_operation)  # noqa: SLF001 (private for application devs, NOT for base implementation)

    @final
    def intersect_sdk_call_service(
        self,
        request: IntersectDirectMessageParams,
        response_handler: INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE | None = None,
        timeout: float = 300.0,
    ) -> list[UUID]:
        """Create an external request that we'll send to a different Service.

        Params:
          - request: the request we want to send out, encapsulated as an IntersectClientMessageParams object
          - response_handler: optional callback for how we want to handle the response from this request.
          - timeout: optional value for how long we should wait on the request, in seconds (default: 300 seconds)

        Returns:
          - list of generated RequestIDs associated with your request. Note that for almost all use cases,
            this list will have only one associated RequestID.

        Raises:
          - pydantic.ValidationError - if the request parameter isn't valid
        """
        return [
            observer.create_external_request(request, response_handler, timeout)
            for observer in self.__intersect_sdk_observers__
        ]

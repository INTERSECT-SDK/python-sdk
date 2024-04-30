"""Basic Capability definitions."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

from typing_extensions import final

from .._internal.constants import BASE_EVENT_ATTR, BASE_RESPONSE_ATTR, BASE_STATUS_ATTR
from .._internal.logger import logger

if TYPE_CHECKING:
    from .._internal.interfaces import IntersectEventObserver


class IntersectBaseCapabilityImplementation:
    """Base class for all capabilities.

    EVERY capability implementation will need to extend this class. Additionally, if you redefine the constructor,
    you MUST call super.__init__() .
    """

    def __init__(self) -> None:
        """This constructor just sets up observers.

        NOTE: If you write your own constructor, you MUST call super.__init__() inside of it. The Service will throw an error if you don't.
        """
        self.__intersect_sdk_observers__: list[IntersectEventObserver] = []
        """
        INTERNAL USE ONLY.

        These are observers that the capability can emit events to.
        """

    def __init_subclass__(cls) -> None:
        """This prevents users from overriding a few key functions."""
        if (
            cls._intersect_sdk_register_observer
            is not IntersectBaseCapabilityImplementation._intersect_sdk_register_observer
            or cls.intersect_sdk_emit_event
            is not IntersectBaseCapabilityImplementation.intersect_sdk_emit_event
        ):
            msg = f"{cls.__name__}: Cannot override functions '_intersect_sdk_register_observer' or 'intersect_sdk_emit_event'"
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

        You MAY NOT emit an event from any function called from an @intersect_status decorated function.

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

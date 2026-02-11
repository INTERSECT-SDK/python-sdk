"""Basic Capability definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from typing_extensions import final

if TYPE_CHECKING:
    from uuid import UUID

    from .._internal.interfaces import IntersectEventObserver
    from ..client_callback_definitions import INTERSECT_CLIENT_EVENT_CALLBACK_TYPE
    from ..config.shared import HierarchyConfig
    from ..service_callback_definitions import (
        INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
    )
    from ..service_definitions import IntersectEventDefinition
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
    This value should ONLY contain alphanumeric characters, hyphens, and underscores. Note case sensitivity; 'HDF' and 'hdf' are different capability names.
    """

    intersect_sdk_events: ClassVar[dict[str, IntersectEventDefinition]] = {}
    """Mapping of event names to IntersectEventDefinitions.

    Override this class with your own configuration value to emit events; by default, the Capability will be configured to emit no events.
    If you did not specify any @intersect_message or @intersect_status functions on your capability, you MUST override this.

    All event keys should ONLY contain alphanumeric characters, hyphens, and underscores. Note case sensitivity; 'temperature' and 'Temperature' are different event keys.
    Any events you specify MUST have a valid IntersectEventDefinition as a value; the associated Service will refuse to start if you don't.

    To emit an event, you can call `capability.intersect_sdk_emit_event(key, value)`. "key" MUST be configured in this dictionary, and "value" MUST match
    the schema you provided for it in the IntersectEventDefinition.

    You are permitted to modify this value as a _class_ _variable_ (i.e. `MyCapabilityImplementation.intersect_sdk_events[dynamic_string_key] = IntersectEventDefinition(...)`) prior to inserting it into the Service. Modifying the value on an instance of this class will do nothing.
    Once this capability is passed into the Service constructor, modifying it any further is pointless.

    Example:

    ```python
    class MyCapability(IntersectBaseCapabilityImplementation):
      intersect_sdk_events: {
        'temperature': IntersectEventDefinition(event_type=float),
        'image': IntersectEventDefinition(event_type=bytes, content_type='image/png'),
      }
    ```
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
            or cls.intersect_sdk_listen_for_service_event
            is not IntersectBaseCapabilityImplementation.intersect_sdk_listen_for_service_event
        ):
            msg = f"{cls.__name__}: Attempted to override a reserved INTERSECT-SDK function (don't start your function names with '__intersect_sdk_', '_intersect_sdk_', or 'intersect_sdk_')"
            raise RuntimeError(msg)

    @final
    def _intersect_sdk_register_observer(self, observer: IntersectEventObserver) -> None:
        """INTERNAL USE ONLY."""
        # observer must have a specific callable function
        self.__intersect_sdk_observers__.append(observer)

    @final
    def intersect_sdk_emit_event(self, event_name: str, event_value: Any) -> None:
        """Emits an event into the INTERSECT system.

        In order to emit an event with the value of 'event_name', you MUST configure the event on the 'intersect_sdk_events' class variable.
        The corresponding event_value you pass in this function MUST match the typing you configure on the IntersectEventDefinition event_value property.

        params:
          event_name: the type of event you are emitting. Note that you must advertise the event on the 'intersect_sdk_events' class variable.
          event_value: the value associated with the event. Note that this value must be accurate to its typing annotation.
        """
        for observer in self.__intersect_sdk_observers__:
            observer._on_observe_event(event_name, event_value, self.intersect_sdk_capability_name)  # noqa: SLF001 (private for application devs, NOT for base implementation)

    @final
    def intersect_sdk_call_service(
        self,
        request: IntersectDirectMessageParams,
        response_handler: INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE | None = None,
        timeout: float = 300.0,
    ) -> list[UUID]:
        """Create an external request that we'll send to a different Service.

        Note: You should generally NOT call this function until after you have initialized the IntersectService class.

        Params:
          - request: the request we want to send out, encapsulated as an IntersectDirectMessageParams object
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

    @final
    def intersect_sdk_listen_for_service_event(
        self,
        service: HierarchyConfig,
        capability_name: str,
        event_name: str,
        response_handler: INTERSECT_CLIENT_EVENT_CALLBACK_TYPE,
    ) -> None:
        """Start listening to events from a specific Service.

        Note: You should generally NOT call this function until after you have initialized the IntersectService class.

        Params:
          - service: The system-of-system hierarchy which points to the specific service
          - capability_name: name of capability on the other service which will fire off the event
          - event_name: The name of the event we want to listen for
          - response_handler: callback for how to handle the reception of an event
            The callback submits these parameters:
            1) message source
            2) name of operation
            3) name of event
            4) payload
        """
        for observer in self.__intersect_sdk_observers__:
            observer.register_event(service, capability_name, event_name, response_handler)

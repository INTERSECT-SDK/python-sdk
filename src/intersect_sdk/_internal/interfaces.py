from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from ..service_callback_definitions import (
        INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
    )
    from ..shared_callback_definitions import (
        IntersectDirectMessageParams,
    )


class IntersectEventObserver(ABC):
    """Abstract definition of an entity which observes an INTERSECT event (i.e. IntersectService).

    Used as the common interface for event emitters (i.e. CapabilityImplementations).
    """

    @abstractmethod
    def _on_observe_event(self, event_name: str, event_value: Any, operation: str) -> None:
        """How to react to an event being fired.

        Args:
            event_name: The key of the event which is fired.
            event_value: The value of the event which is fired.
            operation: The source of the event (generally the function name, not directly invoked by application devs)
        """
        ...

    @abstractmethod
    def create_external_request(
        self,
        request: IntersectDirectMessageParams,
        response_handler: INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE | None = None,
        timeout: float = 300.0,
    ) -> UUID:
        """Observed entity (capabilitiy) tells observer (i.e. service) to send an external request.

        Params:
          - request: the request we want to send out, encapsulated as an IntersectClientMessageParams object
          - response_handler: optional callback for how we want to handle the response from this request.
          - timeout: optional value for how long we should wait on the request, in seconds (default: 300 seconds)

        Returns:
          - generated RequestID associated with your request
        """
        ...

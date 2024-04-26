from abc import ABC, abstractmethod
from typing import Any


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

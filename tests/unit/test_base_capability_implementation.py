from __future__ import annotations

from typing import Any

import pytest
from intersect_sdk import (
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    intersect_event,
    intersect_message,
    intersect_status,
)
from intersect_sdk._internal.interfaces import IntersectEventObserver

# HELPERS ##################


class MockObserver(IntersectEventObserver):
    def __init__(self) -> None:
        self.tracked_events: list[tuple[str, Any, str]] = []

    def _on_observe_event(self, event_name: str, event_value: Any, operation: str) -> None:
        self.tracked_events.append((event_name, event_value, operation))


# TESTS ####################


def test_no_override():
    with pytest.raises(RuntimeError) as ex:

        class BadClass1(IntersectBaseCapabilityImplementation):
            def _intersect_sdk_register_observer(self, observer: IntersectEventObserver) -> None:
                return super()._intersect_sdk_register_observer(observer)

    assert 'BadClass1: Cannot override functions' in str(ex)

    with pytest.raises(RuntimeError) as ex:

        class BadClass2(IntersectBaseCapabilityImplementation):
            def intersect_sdk_emit_event(self, event_name: str, event_value: Any) -> None:
                return super().intersect_sdk_emit_event(event_name, event_value)

    assert 'BadClass2: Cannot override functions' in str(ex)


# Note that the ONLY thing the capability itself checks for are annotated functions.
# The event definitions and overall schema validation are a service-specific feature
def test_functions_dont_emit_events():
    """Functions without annotations and status functions should NOT emit events"""

    class Inner(IntersectBaseCapabilityImplementation):
        def mock_message(self, param: int) -> int:
            ret = param << 1
            self.intersect_sdk_emit_event('mock_message', ret)
            return ret

        def mock_event(self) -> None:
            self.intersect_sdk_emit_event('mock_event', 'hello')

        @intersect_status()
        def mock_status(self) -> str:
            self._inner_function()
            self.intersect_sdk_emit_event('status', 'test')
            return 'test'

        # this function WOULD emit an event if it were called directly, but it gets called through a status function
        @intersect_event(events={'inner': IntersectEventDefinition(event_type=str)})
        def _inner_function(self) -> None:
            self.intersect_sdk_emit_event('inner', 'function')

    # setup
    observer = MockObserver()
    capability = Inner()
    capability._intersect_sdk_register_observer(observer)

    # message mocking
    capability.mock_message(7)
    capability.mock_event()
    capability.mock_status()

    assert len(observer.tracked_events) == 0


def test_functions_emit_events():
    class Inner(IntersectBaseCapabilityImplementation):
        @intersect_message()
        def mock_message(self, param: int) -> int:
            ret = param << 1
            self.intersect_sdk_emit_event('mock_message', ret)
            return ret

        @intersect_event(events={'mock_event': IntersectEventDefinition(event_type=str)})
        def mock_event(self) -> None:
            self.intersect_sdk_emit_event('mock_event', 'hello')

        # can emit any event as long as an earlier function has the event configuration
        # NOTE: The event_type here is invalid, BUT this is something the IntersectService handles.
        @intersect_event(events={'inner': IntersectEventDefinition(event_type=int)})
        def outer_function(self) -> None:
            self._inner_function()

        def _inner_function(self) -> None:
            self.intersect_sdk_emit_event('inner', 'function')

    # setup
    observer = MockObserver()
    capability = Inner()
    capability._intersect_sdk_register_observer(observer)

    # message mocking
    capability.mock_message(2)
    assert len(observer.tracked_events) == 1
    capability.mock_event()
    assert len(observer.tracked_events) == 2
    capability.outer_function()
    assert len(observer.tracked_events) == 3

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from intersect_sdk import (
    INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
    IntersectBaseCapabilityImplementation,
    IntersectDirectMessageParams,
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
        self.registered_requests: dict[
            UUID,
            tuple[IntersectDirectMessageParams, INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE | None],
        ] = {}

    def _on_observe_event(self, event_name: str, event_value: Any, operation: str) -> None:
        self.tracked_events.append((event_name, event_value, operation))

    def create_external_request(
        self,
        request: IntersectDirectMessageParams,
        response_handler: INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE | None = None,
        timeout: float = 300.0,
    ) -> UUID:
        request_id = uuid4()
        self.registered_requests[request_id] = (request, response_handler)
        return request_id


# TESTS ####################


def test_no_override():
    with pytest.raises(RuntimeError) as ex:

        class BadClass1(IntersectBaseCapabilityImplementation):
            def _intersect_sdk_register_observer(self, observer: IntersectEventObserver) -> None:
                return super()._intersect_sdk_register_observer(observer)

    assert 'BadClass1: Attempted to override a reserved INTERSECT-SDK function' in str(ex)

    with pytest.raises(RuntimeError) as ex:

        class BadClass2(IntersectBaseCapabilityImplementation):
            def intersect_sdk_emit_event(self, event_name: str, event_value: Any) -> None:
                return super().intersect_sdk_emit_event(event_name, event_value)

    assert 'BadClass2: Attempted to override a reserved INTERSECT-SDK function' in str(ex)

    with pytest.raises(RuntimeError) as ex:

        class BadClass3(IntersectBaseCapabilityImplementation):
            def intersect_sdk_call_service(
                self,
                request: IntersectDirectMessageParams,
                response_handler: INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE | None = None,
            ) -> None:
                return super().intersect_sdk_call_service(request, response_handler)

    assert 'BadClass3: Attempted to override a reserved INTERSECT-SDK function' in str(ex)


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


def test_functions_handle_requests():
    class Inner(IntersectBaseCapabilityImplementation):
        def __init__(self) -> None:
            super().__init__()
            self.tracked_responses = []

        @intersect_message()
        def mock_request_flow(self, fake_request_value: str) -> UUID:
            return self.intersect_sdk_call_service(
                IntersectDirectMessageParams(
                    destination='fake.fake.fake.fake.fake',
                    operation='Fake.fake',
                    payload=fake_request_value,
                ),
                self._mock_other_service_callback,
                300.0,
            )[0]

        def _mock_other_service_callback(
            self,
            _source: str,
            _operation: str,
            _has_error: bool,
            param: INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
        ):
            self.tracked_responses.append(param)

    # setup
    observer = MockObserver()
    capability = Inner()
    capability._intersect_sdk_register_observer(observer)

    # mock making the request and setting up the response handler
    body = 'ping'
    reqid = capability.mock_request_flow(body)
    assert len(observer.registered_requests) == 1
    req, res = observer.registered_requests[reqid]
    assert req.payload == body

    # mock calling the response handler
    res('fake.fake.fake.fake.fake', 'Fake.fake', False, 'pong')
    assert len(capability.tracked_responses) == 1
    assert capability.tracked_responses[0] == 'pong'

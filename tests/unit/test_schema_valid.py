import json
from pathlib import Path

from intersect_sdk import (
    IntersectBaseCapabilityImplementation,
    IntersectDataHandler,
    IntersectEventDefinition,
    get_schema_from_capability_implementations,
    intersect_message,
    intersect_status,
)
from intersect_sdk._internal.schema import get_schema_and_functions_from_capability_implementations
from tests.fixtures.example_schema import (
    FAKE_HIERARCHY_CONFIG,
    DummyCapabilityImplementation,
)

# HELPERS ################


def get_fixture_path(fixture: str):
    return Path(__file__).absolute().parents[1] / 'fixtures' / fixture


# MINIMAL ANNOTATION TESTS ######################


def test_minimal_intersect_annotations() -> None:
    class CapWithMessage(IntersectBaseCapabilityImplementation):
        intersect_sdk_capability_name = 'CapWithMessage'

        @intersect_message
        def message_function(self, theinput: int) -> int:
            return theinput * 4

    class CapWithEvent(IntersectBaseCapabilityImplementation):
        intersect_sdk_capability_name = 'CapWithEvent'
        intersect_sdk_events = {'event': IntersectEventDefinition(event_type=str)}

        def event_function(self):
            self.intersect_sdk_emit_event('event', 'emitted_value')

    class CapWithStatus(IntersectBaseCapabilityImplementation):
        intersect_sdk_capability_name = 'CapWithStatus'

        @intersect_status
        def status_function(self) -> str:
            return 'Up'

    schemas = get_schema_from_capability_implementations(
        [
            CapWithEvent,
            CapWithMessage,
            CapWithStatus,
        ],
        FAKE_HIERARCHY_CONFIG,
    )
    # this will also include the universal capability
    assert len(schemas['capabilities']) == 4


# FIXTURE TESTS ##################


def test_schema_comparison():
    with Path.open(get_fixture_path('example_schema.json'), 'rb') as f:
        expected_schema = json.load(f)
    actual_schema = get_schema_from_capability_implementations(
        [DummyCapabilityImplementation],
        FAKE_HIERARCHY_CONFIG,
    )
    assert expected_schema == actual_schema


def test_verify_status_fn() -> None:
    # NOTE: this construction will not include the default intersect_sdk capability, however this is an internal function which is normally only called after that capability is injected
    (schema, function_map, _, status_list) = (
        get_schema_and_functions_from_capability_implementations(
            [DummyCapabilityImplementation], FAKE_HIERARCHY_CONFIG, set()
        )
    )

    dummy_capability = status_list[0]

    assert (
        dummy_capability.capability_name
        is DummyCapabilityImplementation.intersect_sdk_capability_name
    )
    assert dummy_capability.function_name == 'get_status'
    assert (
        dummy_capability.capability_name
        not in schema['capabilities']['DummyCapability']['endpoints']
    )

    scoped_name = f'{dummy_capability.capability_name}.{dummy_capability.function_name}'
    assert scoped_name in function_map
    assert dummy_capability.serializer == function_map[scoped_name].response_adapter
    assert function_map[scoped_name].request_adapter is None
    assert (
        dummy_capability.serializer.json_schema() == schema['components']['schemas']['DummyStatus']
    )


def test_verify_attributes():
    (
        _,
        function_map,
        _,
        _,
    ) = get_schema_and_functions_from_capability_implementations(
        [DummyCapabilityImplementation], FAKE_HIERARCHY_CONFIG, set()
    )
    # test defaults
    assert (
        function_map['DummyCapability.verify_float_dict'].response_data_transfer_handler
        == IntersectDataHandler.MESSAGE
    )
    assert function_map['DummyCapability.verify_nested'].request_content_type == 'application/json'
    assert function_map['DummyCapability.verify_nested'].response_content_type == 'application/json'
    assert function_map['DummyCapability.verify_nested'].strict_validation is False

    # test non-defaults
    assert (
        function_map['DummyCapability.verify_nested'].response_data_transfer_handler
        == IntersectDataHandler.MINIO
    )
    assert function_map['DummyCapability.ip4_to_ip6'].response_content_type == 'application/json'
    assert function_map['DummyCapability.test_path'].request_content_type == 'application/json'
    assert function_map['DummyCapability.calculate_3n_plus_1'].strict_validation is True


def test_multiple_status_functions_across_capabilities() -> None:
    class CapabilityName1(IntersectBaseCapabilityImplementation):
        intersect_sdk_capability_name = '1'

        @intersect_message()
        def valid_function_1(self, param: str) -> str: ...

        @intersect_status
        def status_function_1(self) -> str: ...

    class CapabilityName2(IntersectBaseCapabilityImplementation):
        intersect_sdk_capability_name = '2'

        @intersect_message()
        def valid_function_2(self, param: str) -> str: ...

        @intersect_status
        def status_function_2(self) -> str: ...

    schema = get_schema_from_capability_implementations(
        [CapabilityName1, CapabilityName2], FAKE_HIERARCHY_CONFIG
    )

    assert len(schema['capabilities']) == 3
    for capability in schema['capabilities'].values():
        assert 'status' in capability

import json
from pathlib import Path

from intersect_sdk import IntersectDataHandler
from intersect_sdk._internal.schema import get_schema_and_functions_from_capability_implementation
from intersect_sdk.schema import get_schema_from_capability_implementation

from tests.fixtures.example_schema import (
    FAKE_HIERARCHY_CONFIG,
    DummyCapabilityImplementation,
)

# HELPERS ################


def get_fixture_path(fixture: str):
    return Path(__file__).absolute().parents[1] / 'fixtures' / fixture


# TESTS ##################


def test_schema_comparison():
    with Path.open(get_fixture_path('example_schema.json'), 'rb') as f:
        expected_schema = json.load(f)
    actual_schema = get_schema_from_capability_implementation(
        DummyCapabilityImplementation,
        FAKE_HIERARCHY_CONFIG,
    )
    assert expected_schema == actual_schema


def test_verify_status_fn():
    (
        schema,
        function_map,
        _,
        status_fn_name,
        status_type_adapter,
    ) = get_schema_and_functions_from_capability_implementation(
        DummyCapabilityImplementation, FAKE_HIERARCHY_CONFIG, set()
    )
    assert status_fn_name == 'get_status'

    assert status_fn_name in function_map
    assert status_fn_name not in schema['channels']
    assert status_type_adapter == function_map[status_fn_name].response_adapter
    assert function_map[status_fn_name].request_adapter is None
    assert status_type_adapter.json_schema() == schema['components']['schemas']['DummyStatus']


def test_verify_attributes():
    _, function_map, _, _, _ = get_schema_and_functions_from_capability_implementation(
        DummyCapabilityImplementation,
        FAKE_HIERARCHY_CONFIG,
        set(),
    )
    # test defaults
    assert (
        function_map['verify_float_dict'].response_data_transfer_handler
        == IntersectDataHandler.MESSAGE
    )
    assert function_map['verify_nested'].request_content_type == 'application/json'
    assert function_map['verify_nested'].response_content_type == 'application/json'
    assert function_map['verify_nested'].strict_validation is False

    # test non-defaults
    assert (
        function_map['verify_nested'].response_data_transfer_handler == IntersectDataHandler.MINIO
    )
    assert function_map['ip4_to_ip6'].response_content_type == 'application/json'
    assert function_map['test_path'].request_content_type == 'application/json'
    assert function_map['calculate_weird_algorithm'].strict_validation is True

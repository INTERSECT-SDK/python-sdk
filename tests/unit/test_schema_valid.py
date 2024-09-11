import json
from pathlib import Path

from intersect_sdk import IntersectDataHandler, IntersectMimeType
from intersect_sdk._internal.constants import (
    REQUEST_CONTENT,
    RESPONSE_CONTENT,
    RESPONSE_DATA,
    STRICT_VALIDATION,
)
from intersect_sdk._internal.schema import get_schema_and_functions_from_capability_implementations
from intersect_sdk.schema import get_schema_from_capability_implementations

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
    actual_schema = get_schema_from_capability_implementations(
        [DummyCapabilityImplementation],
        FAKE_HIERARCHY_CONFIG,
    )
    assert expected_schema == actual_schema


def test_verify_status_fn():
    (schema, function_map, _, status_fn_capability, status_fn_name, status_type_adapter) = (
        get_schema_and_functions_from_capability_implementations(
            [DummyCapabilityImplementation], FAKE_HIERARCHY_CONFIG, set()
        )
    )
    assert status_fn_capability is DummyCapabilityImplementation
    assert status_fn_name == 'get_status'
    assert status_fn_name not in schema['capabilities']

    scoped_name = f'{status_fn_capability.intersect_sdk_capability_name}.{status_fn_name}'
    assert scoped_name in function_map
    assert status_type_adapter == function_map[scoped_name].response_adapter
    assert function_map[scoped_name].request_adapter is None
    assert status_type_adapter.json_schema() == schema['components']['schemas']['DummyStatus']


def test_verify_attributes():
    _, function_map, _, _, _, _ = get_schema_and_functions_from_capability_implementations(
        [DummyCapabilityImplementation], FAKE_HIERARCHY_CONFIG, set()
    )
    # test defaults
    assert (
        getattr(function_map['DummyCapability.verify_float_dict'].method, RESPONSE_DATA)
        == IntersectDataHandler.MESSAGE
    )
    assert (
        getattr(function_map['DummyCapability.verify_nested'].method, REQUEST_CONTENT)
        == IntersectMimeType.JSON
    )
    assert (
        getattr(function_map['DummyCapability.verify_nested'].method, RESPONSE_CONTENT)
        == IntersectMimeType.JSON
    )
    assert getattr(function_map['DummyCapability.verify_nested'].method, STRICT_VALIDATION) is False

    # test non-defaults
    assert (
        getattr(function_map['DummyCapability.verify_nested'].method, RESPONSE_DATA)
        == IntersectDataHandler.MINIO
    )
    assert (
        getattr(function_map['DummyCapability.ip4_to_ip6'].method, RESPONSE_CONTENT)
        == IntersectMimeType.STRING
    )
    assert (
        getattr(function_map['DummyCapability.test_path'].method, REQUEST_CONTENT)
        == IntersectMimeType.STRING
    )
    assert (
        getattr(function_map['DummyCapability.calculate_weird_algorithm'].method, STRICT_VALIDATION)
        is True
    )

import json
from pathlib import Path

from intersect_sdk import IntersectDataHandler, IntersectMimeType
from intersect_sdk._internal.constants import (
    REQUEST_CONTENT,
    RESPONSE_CONTENT,
    RESPONSE_DATA,
    STRICT_VALIDATION,
)
from intersect_sdk.schema import get_schema_and_functions_from_model, get_schema_from_model

from tests.fixtures.example_schema import (
    FAKE_HIERARCHY_CONFIG,
    DummyCapabilityImplementation,
)

# HELPERS ################


def get_fixture_path(fixture: str):
    return Path(__file__).absolute().parents[1] / 'fixtures' / fixture


# TESTS ##################


def test_schema_comparision():
    with open(get_fixture_path('example_schema.json'), 'rb') as f:
        expected_schema = json.load(f)
    actual_schema = get_schema_from_model(
        DummyCapabilityImplementation, FAKE_HIERARCHY_CONFIG, '0.0.1'
    )
    assert expected_schema == actual_schema


def test_verify_status_fn():
    schema, function_map, status_fn_name, status_type_adapter = get_schema_and_functions_from_model(
        DummyCapabilityImplementation, FAKE_HIERARCHY_CONFIG, '0.0.1'
    )
    assert status_fn_name == 'get_status'

    assert status_fn_name in function_map
    assert status_fn_name not in schema['channels']
    assert status_type_adapter == function_map[status_fn_name].response_adapter
    assert function_map[status_fn_name].request_adapter is None
    assert status_type_adapter.json_schema() == schema['components']['schemas']['DummyStatus']


def test_verify_attributes():
    _, function_map, _, _ = get_schema_and_functions_from_model(
        DummyCapabilityImplementation, FAKE_HIERARCHY_CONFIG, '0.0.1'
    )
    # test defaults
    assert (
        getattr(function_map['verify_float_dict'].method, RESPONSE_DATA)
        == IntersectDataHandler.MESSAGE
    )
    assert (
        getattr(function_map['verify_nested'].method, REQUEST_CONTENT)
        == IntersectMimeType.JSON.value
    )
    assert (
        getattr(function_map['verify_nested'].method, RESPONSE_CONTENT)
        == IntersectMimeType.JSON.value
    )
    assert getattr(function_map['verify_nested'].method, STRICT_VALIDATION) is False

    # test non-defaults
    assert (
        getattr(function_map['verify_nested'].method, RESPONSE_DATA) == IntersectDataHandler.MINIO
    )
    assert (
        getattr(function_map['ip4_to_ip6'].method, RESPONSE_CONTENT)
        == IntersectMimeType.STRING.value
    )
    assert (
        getattr(function_map['test_path'].method, REQUEST_CONTENT) == IntersectMimeType.STRING.value
    )
    assert getattr(function_map['calculate_weird_algorithm'].method, STRICT_VALIDATION) is True

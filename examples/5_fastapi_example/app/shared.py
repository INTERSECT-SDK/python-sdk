import datetime

from pydantic import BaseModel

from intersect_sdk import HierarchyConfig

CAPABILITY_NAME = 'fastapi_sample_capability'
EVENT_NAME = 'fastapi_event'


class MockInputType(BaseModel):
    """mock data type with expanded out fields."""

    param_1: float
    param_2: int
    param_3: int


class MockOutputType(BaseModel):
    """mock output data type."""

    computed_value: float
    parse_time: datetime.datetime = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    message: str = ''


def do_mock_compute(input_value: MockInputType) -> MockOutputType:
    """Generic computation."""
    return MockOutputType(
        computed_value=(input_value.param_1 + input_value.param_2 * input_value.param_3),
        parse_time=datetime.datetime.now(datetime.timezone.utc),
    )


def get_service_hierarchy() -> HierarchyConfig:
    """Shared hierarchy."""
    return HierarchyConfig(
        organization='fastapi-organization',
        facility='fastapi-facility',
        system='fastapi-system',
        subsystem='fastapi-subsystem',
        service='fastapi-service',
    )

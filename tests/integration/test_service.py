import pytest
from intersect_sdk import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    IntersectService,
    IntersectServiceConfig,
)

from tests.fixtures.example_schema import DummyCapabilityImplementation, FAKE_HIERARCHY_CONFIG


@pytest.fixture()
def intersect_service() -> IntersectService:
    return IntersectService(
        DummyCapabilityImplementation(),
        IntersectServiceConfig(
            hierarchy=FAKE_HIERARCHY_CONFIG,
            schema_version='0.0.1',
            data_stores=DataStoreConfigMap(
                minio=[
                    DataStoreConfig(
                        username='AKIAIOSFODNN7EXAMPLE',
                        password='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                        port=9000,
                    )
                ]
            ),
            brokers=[
                ControlPlaneConfig(
                    username='intersect_username',
                    password='intersect_password',
                    port=1883,
                    protocol='mqtt3.1.1',
                ),
            ],
            status_interval=30.0,
        ),
    )


# TESTS ################


def test_control_plane_connections(intersect_service: IntersectService):
    assert intersect_service.is_connected() is False
    intersect_service.startup()
    assert intersect_service.is_connected() is True
    intersect_service.shutdown()
    assert intersect_service.is_connected() is False

    # we have one channel (even if we're disconnected) ...
    assert len(intersect_service._control_plane_manager.get_subscription_channels()) == 1
    # ... and one callback function for this channel
    assert (
        len(next(iter(intersect_service._control_plane_manager.get_subscription_channels()))) == 1
    )

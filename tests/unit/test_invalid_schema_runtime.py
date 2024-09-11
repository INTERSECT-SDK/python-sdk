"""
This module runs some edge cases: we need to verify that some schemas are invalid.

HOWEVER - we can only do this through the Service class, as get_schema_from_capability_implementations does not
check that service configuration is valid.
"""

import pytest
from intersect_sdk import (
    ControlPlaneConfig,
    IntersectBaseCapabilityImplementation,
    IntersectDataHandler,
    IntersectService,
    IntersectServiceConfig,
    intersect_message,
)

from ..fixtures.example_schema import FAKE_HIERARCHY_CONFIG


class CapabilityWithMinio(IntersectBaseCapabilityImplementation):
    intersect_sdk_capability_name = 'TestMinioCapability'

    @intersect_message(response_data_transfer_handler=IntersectDataHandler.MINIO)
    def arbitrary_function(self, param: int) -> int: ...


def test_minio_not_allowed_without_config(caplog: pytest.LogCaptureFixture):
    cap = CapabilityWithMinio()
    # note that despite the broker configuration, you do not actually need a broker running for this test
    conf = IntersectServiceConfig(
        hierarchy=FAKE_HIERARCHY_CONFIG,
        brokers=[
            ControlPlaneConfig(
                username='intersect_username',
                password='intersect_password',
                port=1883,
                protocol='mqtt3.1.1',
            ),
        ],
    )
    with pytest.raises(SystemExit):
        IntersectService([cap], conf)
    assert "function 'arbitrary_function' should not set response_data_type as 1" in caplog.text

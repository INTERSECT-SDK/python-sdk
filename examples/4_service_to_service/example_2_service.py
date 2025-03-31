"""Second Service for example."""

import logging

from intersect_sdk import (
    ControlPlaneConfig,
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_message,
    intersect_status,
)
from intersect_sdk.config.shared import BrokerConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExampleServiceTwoCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Service 2 Capability."""

    intersect_sdk_capability_name = 'ServiceTwo'

    @intersect_status()
    def status(self) -> str:
        """Basic status function which returns a hard-coded string."""
        return 'Up'

    @intersect_message
    def test_service(self, text: str) -> str:
        """Returns the text given along with acknowledgement."""
        return f'Acknowledging service one text -> {text}'


if __name__ == '__main__':
    broker_configs = [
        {'host': 'localhost', 'port': 1883},
    ]

    brokers = [
        ControlPlaneConfig(
            protocol='mqtt3.1.1',
            username='intersect_username',
            password='intersect_password',
            brokers=[BrokerConfig(**broker) for broker in broker_configs],
        )
    ]
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='example-organization',
            facility='example-facility',
            system='example-system',
            subsystem='example-subsystem',
            service='service-two',
        ),
        status_interval=30.0,
        brokers=brokers,
    )
    capability = ExampleServiceTwoCapabilityImplementation()
    service = IntersectService([capability], config)
    logger.info('Starting Service 2, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
    )

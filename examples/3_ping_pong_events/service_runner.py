"""Common functionality between all of the Service classes."""

import logging
from abc import ABC, abstractmethod

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
)

logger = logging.getLogger(__name__)


class P_ngBaseCapabilityImplementation(IntersectBaseCapabilityImplementation, ABC):  # noqa: N801
    """Common interface definitions, no implementations here."""

    @abstractmethod
    def after_service_startup(self) -> None:
        """Common function implemented by the various P-NG capabilities after the service starts up."""


def run_service(capability: P_ngBaseCapabilityImplementation) -> None:
    """The idea behind the two services is that each one will emit a unique event.

    The interesting configuration mostly happens in the Client, look at that one for details.
    """
    from_config_file = {
        'data_stores': {
            'minio': [
                {
                    'username': 'AKIAIOSFODNN7EXAMPLE',
                    'password': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                    'port': 9000,
                },
            ],
        },
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }
    service_name = capability.__class__.__name__[:4].lower()
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='p-ng-organization',
            facility='p-ng-facility',
            system='p-ng-system',
            subsystem='p-ng-subsystem',
            service=f'{service_name}-service',
        ),
        status_interval=30.0,
        **from_config_file,
    )
    service = IntersectService(capability, config)
    logger.info('Starting %s_service, use Ctrl+C to exit.', service_name)

    """
    Here, we provide the after_service_startup function on the capability as a post startup callback.

    This ensures we don't emit any events until we've actually started up our Service.
    """
    default_intersect_lifecycle_loop(
        service, post_startup_callback=capability.after_service_startup
    )

"""Client for service to service example.

Listens for events from the exposed_service, and prints each one out.
Once it gets two events, it terminates itself.
"""

import logging

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    ControlPlaneConfig,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    default_intersect_lifecycle_loop,
)
from intersect_sdk.config.shared import BrokerConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleOrchestrator:
    """Simply contains an event callback for events from the exposed service.

    In this example, we just want to receive two events from the exposed service before killing the client.
    """

    def __init__(self) -> None:
        """Straightforward constructor, just initializes global variable which counts events."""
        self.got_first_event = False

    def event_callback(
        self, _source: str, _operation: str, _event_name: str, payload: INTERSECT_JSON_VALUE
    ) -> None:
        """This simply prints the event from the exposed service to your console.

        Params:
          source: the source of the response message.
          operation: the name of the function we called in the original message.
          _has_error: Boolean value which represents an error.
          payload: Value of the response from the Service.
        """
        print(payload)
        if self.got_first_event:
            # break out of pubsub loop
            raise Exception
        self.got_first_event = True
        # empty return, don't send any additional messages or modify the events listened to


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

    # Listen for an event on the exposed service
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            services_to_start_listening_for_events=[
                'example-organization.example-facility.example-system.example-subsystem.exposed-service'
            ],
        ),
        brokers=brokers,
    )
    orchestrator = SampleOrchestrator()
    client = IntersectClient(
        config=config,
        event_callback=orchestrator.event_callback,
    )
    default_intersect_lifecycle_loop(
        client,
    )

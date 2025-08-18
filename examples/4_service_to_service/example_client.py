"""Client for service to service example.

Kicks off example by sending message to service one, and then
waits for an event from service one to confirm the messages were passed between the two services properly.

"""

import logging

from intersect_sdk import (
    INTERSECT_RESPONSE_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectDirectMessageParams,
    IntersectEventMessageParams,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleOrchestrator:
    """Simply contains an event callback for events from Service 1."""

    def __init__(self) -> None:
        """Straightforward constructor, just initializes global variable which counts events."""
        self.got_first_event = False

    def event_callback(
        self,
        _source: str,
        _capability_name: str,
        _event_name: str,
        payload: INTERSECT_RESPONSE_VALUE,
    ) -> None:
        """This simply prints the event from Service 1 to your console.

        Params:
          source: the source of the response message.
          capability_name: the name of the capability which emitted the event.
          event_name: Name of the event.
          payload: Value of the response from the Service.
        """
        print(payload)
        if self.got_first_event:
            # break out of pubsub loop
            raise Exception
        self.got_first_event = True
        # empty return, don't send any additional messages or modify the events listened to


if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt5.0',
            },
        ],
    }

    # The counter will start after the initial message.
    # If the service is already active and counting, this may do nothing.
    initial_messages = [
        IntersectDirectMessageParams(
            destination='example-organization.example-facility.example-system.example-subsystem.service-one',
            operation='ServiceOne.pass_text_to_service_2',
            payload='Kicking off the example!',
        )
    ]
    events = [
        IntersectEventMessageParams(
            hierarchy='example-organization.example-facility.example-system.example-subsystem.service-one',
            capability_name='ServiceOne',
            event_name='response_event',
        )
    ]
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            messages_to_send=initial_messages,
            services_to_start_listening_for_events=events,
        ),
        **from_config_file,
    )
    orchestrator = SampleOrchestrator()
    client = IntersectClient(
        config=config,
        event_callback=orchestrator.event_callback,
    )
    default_intersect_lifecycle_loop(
        client,
    )

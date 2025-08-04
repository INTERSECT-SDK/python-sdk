import logging

from intersect_sdk import (
    INTERSECT_RESPONSE_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectEventMessageParams,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)


def get_event_message_params(png: str) -> IntersectEventMessageParams:
    """Generate the event information we'll handle based on the value of 'png'.

    We always want to pass in a new object; don't mutate a persistent object.
    """
    return IntersectEventMessageParams(
        hierarchy=f'p-ng-organization.p-ng-facility.p-ng-system.p-ng-subsystem.{png}-service',
        capability_name=png,
        event_name=png,
    )


class SampleOrchestrator:
    """Basic orchestrator with an event callback.

    The event callback switches between listening to 'ping' and 'pong' events; it never listens to both simultaneously.
    """

    MAX_EVENTS_TO_PROCESS = 4

    def __init__(self) -> None:
        """Straightforward constructor, just initializes global variable which counts events."""
        self.events_encountered = 0

    def event_callback(
        self,
        _source: str,
        _capability_name: str,
        event_name: str,
        payload: INTERSECT_RESPONSE_VALUE,
    ) -> IntersectClientCallback:
        """Handles events from two Services at once.

        With this handler, the order of instructions goes like this:

        1. Listen for a ping event.
        2. On ping event - Start listening for pong events and stop listening for ping events.
        3. On pong event - Start listening for ping events and stop listening for pong events.
        4. Repeat steps 2-3 until we have processed the maximum number of events we want to.
        """
        self.events_encountered += 1
        print(payload)
        if self.events_encountered == self.MAX_EVENTS_TO_PROCESS:
            raise Exception

        # In this case, we can check any of the source, the capability_name, or the event_name. For maximum robustness, you should check all three values.
        if event_name == 'ping':
            return IntersectClientCallback(
                services_to_start_listening_for_events=[get_event_message_params('pong')],
                services_to_stop_listening_for_events=[get_event_message_params('ping')],
            )
        return IntersectClientCallback(
            services_to_start_listening_for_events=[get_event_message_params('ping')],
            services_to_stop_listening_for_events=[get_event_message_params('pong')],
        )


if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }

    # we initially only listen for ping service events,
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            services_to_start_listening_for_events=[
                get_event_message_params('ping'),
            ]
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

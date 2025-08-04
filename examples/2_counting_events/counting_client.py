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


class SampleOrchestrator:
    """This class contains the callback function.

    It uses a class because we want to modify our own state from the callback function.

    State is managed through counting the events we receive - we'll process a certain number of events, then stop.
    """

    MAX_EVENTS_TO_PROCESS = 3

    def __init__(self) -> None:
        """Straightforward constructor, initializes a global variable we modify on getting an event."""
        self.events_encountered = 0

    def event_callback(
        self,
        _source: str,
        _capability_name: str,
        _event_name: str,
        payload: INTERSECT_RESPONSE_VALUE,
    ) -> None:
        """Handles events from the Counting Service.

        We want to process 3 events and then stop processing events. With each event, we'll print out the emitted event.

        In this case, since we don't send out any messages or switch the events we listen to, we can just return None.
        If we DID want to modify this, we would return an IntersectClientCallback object.

        Params:
          - _source: the source of the event (in this instance, it will always be the counting service)
          - _capability_name: the name of the capability from the service which emitted the event. In this case it will always be 'CountingExample'.
          - _event_name: the name of the event. In this case it will always be 'increment_counter'.
          - payload: the actual value of the emitted event. In this case it will always be an integer (3, 27, 81, 243, ...)
        """
        # this check isn't necessary in this instance, but given that events are completely asynchronous
        # it can be good to verify that we only handle the intended events
        if self.events_encountered > self.MAX_EVENTS_TO_PROCESS:
            return
        self.events_encountered += 1
        print(payload)
        if self.events_encountered == self.MAX_EVENTS_TO_PROCESS:
            raise Exception


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

    # start listening to events from the counting service
    events = [
        IntersectEventMessageParams(
            hierarchy='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
            capability_name='CountingExample',
            event_name='increment_counter',
        )
    ]
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
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

import logging

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)


class SampleOrchestrator:
    """This class contains the callback function.

    It uses a class because we want to modify our own state from the callback function.

    State is managed through a message stack. We initialize a request-reply-request-reply... chain with the Service,
    and the chain ends once we've popped all messages from our message stack.
    """

    MAX_EVENTS_TO_PROCESS = 3

    def __init__(self) -> None:
        """Basic constructor for the orchestrator class, call before creating the IntersectClient.

        As the only thing exposed to the Client is the callback function, the orchestrator class may otherwise be
        created and managed as the SDK developer sees fit.

        The messages are initialized in the order they are sent for readability purposes.
        The message stack is a tuple: the message, and the time to wait before sending it.

        All approximations in comments come from the first run against the service, but the values can potentially vary
        if you run the client multiple times!
        """
        self.events_encountered = 0

    def event_callback(
        self, _source: str, _operation: str, _event_name: str, payload: INTERSECT_JSON_VALUE
    ) -> None:
        """Handles events from the Counting Service.

        We want to process 3 events and then stop processing events. With each event, we'll print out the emitted event.

        In this case, since we don't send out any messages or switch the events we listen to, we can just return None.
        If we DID want to modify this, we would return an IntersectClientCallback object.

        Params:
          - _source: the source of the event (in this instance, it will always be the counting service)
          - _operation: the name of the operation from the service which emitted the event. Sometimes this comes from a message.
              In this case it will always be 'increment_counter_function', since that's the function the event was configured on.
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

    # start listening to events from the counting service
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            services_to_start_listening_for_events=[
                'counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
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

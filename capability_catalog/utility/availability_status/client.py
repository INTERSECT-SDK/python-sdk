import json
import logging
import time

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)

from capability_catalog.utility.availability_status.types import (
    AvailabilityStatus,
    AvailabilityStatusEnum,
    AvailabilityStatusResult,
    SetAvailabilityStatusCommand
)

logging.basicConfig(level=logging.INFO)


class SampleOrchestrator:
    """This class contains the callback function.

    It uses a class because we want to modify our own state from the callback function.

    State is managed through a message stack. We initialize a request-reply-request-reply... chain with the Service,
    and the chain ends once we've popped all messages from our message stack.
    """
    def __init__(self) -> None:
        """Basic constructor for the orchestrator class, call before creating the IntersectClient.

        As the only thing exposed to the Client is the callback function, the orchestrator class may otherwise be
        created and managed as the SDK developer sees fit.

        The messages are initialized in the order they are sent for readability purposes.
        The message stack is a list of tuples, each with the message and the time to wait before sending it.
        """
        self.message_stack = [
            # wait 1 second before setting initial status - AVAILABLE
            (
                IntersectClientMessageParams(
                    destination='my-organization.my-facility.my-system.my-subsystem.my-service',
                    operation='AvailabilityStatus.set_availability_status',
                    payload=SetAvailabilityStatusCommand(new_status=AvailabilityStatusEnum.AVAILABLE,
                                                               status_description="initial status"),
                ),
                1.0,
            ),
            # wait 3 seconds before getting current status, which should be AVAILABLE
            (
                IntersectClientMessageParams(
                    destination='my-organization.my-facility.my-system.my-subsystem.my-service',
                    operation='AvailabilityStatus.get_availability_status',
                    payload=True,
                ),
                3.0,
            ),
            # wait 5 seconds before setting new status - DEGRADED
            (
                IntersectClientMessageParams(
                    destination='my-organization.my-facility.my-system.my-subsystem.my-service',
                    operation='AvailabilityStatus.set_availability_status',
                    payload=SetAvailabilityStatusCommand(new_status=AvailabilityStatusEnum.DEGRADED,
                                                               status_description="service degraded"),
                ),
                5.0,
            ),
            # wait 2 seconds before getting current status, which should be DEGRADED
            (
                IntersectClientMessageParams(
                    destination='my-organization.my-facility.my-system.my-subsystem.my-service',
                    operation='AvailabilityStatus.get_availability_status',
                    payload=None,
                ),
                2.0,
            ),
            # wait 1 second before setting new status - AVAILABLE
            (
                IntersectClientMessageParams(
                    destination='my-organization.my-facility.my-system.my-subsystem.my-service',
                    operation='AvailabilityStatus.set_availability_status',
                    payload=SetAvailabilityStatusCommand(new_status=AvailabilityStatusEnum.AVAILABLE,
                                                               status_description="service restored"),
                ),
                1.0,
            ),
            # wait 20 seconds before getting new status, which should be AVAILABLE
            (
                IntersectClientMessageParams(
                    destination='my-organization.my-facility.my-system.my-subsystem.my-service',
                    operation='AvailabilityStatus.get_availability_status',
                    payload=None,
                ),
                20.0,
            ),
        ]
        self.message_stack.reverse()

    def client_callback(
        self, source: str, operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        """ Processes service responses for Availability Status sample client
        """
        print('Source:', json.dumps(source))
        print('Operation:', json.dumps(operation))
        print('Payload:', json.dumps(payload))
        print()
        if not self.message_stack:
            # break out of pub/sub loop
            raise Exception
        message, wait_time = self.message_stack.pop()
        time.sleep(wait_time)
        return IntersectClientCallback(messages_to_send=[message])
    

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
    # The counter will start after the initial message.
    # If the service is already active and counting, this may do nothing.
    initial_messages = [
        IntersectClientMessageParams(
            destination='my-organization.my-facility.my-system.my-subsystem.my-service',
            operation='AvailabilityStatus.get_availability_status',
            payload=None,
        )
    ]
    orchestrator = SampleOrchestrator()
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(messages_to_send=initial_messages),
        **from_config_file,
    )
    client = IntersectClient(
        config=config,
        user_callback=orchestrator.client_callback,
    )
    default_intersect_lifecycle_loop(client)

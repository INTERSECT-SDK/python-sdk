import logging
import time
from typing import Any, Dict

from intersect_sdk import (
    IntersectClient,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)


class SampleOrchestrator:
    def __init__(self) -> None:
        # the messages are initialized in the order they are sent for readability purposes
        # the message stack is a tuple: the message, and the time to wait before sending it.
        #
        # all approximations in comments come from the first run against the service, but the values can potentially vary
        # if you run the client multiple times!
        self.message_stack = [
            # wait 5 seconds before stopping the counter. "Count" in response will be approx. 6
            (
                IntersectClientMessageParams(
                    destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
                    operation='stop_count',
                    payload=None,
                ),
                5.0,
            ),
            # start the counter up again - it will not be 0 at this point! "Count" in response will be approx. 7
            (
                IntersectClientMessageParams(
                    destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
                    operation='start_count',
                    payload=None,
                ),
                1.0,
            ),
            # reset the counter, but have it immediately start running again. "Count" in response will be approx. 10
            (
                IntersectClientMessageParams(
                    destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
                    operation='reset_count',
                    payload=True,
                ),
                3.0,
            ),
            # reset the counter, but don't have it run again. "Count" in response will be approx. 6
            (
                IntersectClientMessageParams(
                    destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
                    operation='reset_count',
                    payload=False,
                ),
                5.0,
            ),
            # start the counter back up. "Count" in response will be approx. 1
            (
                IntersectClientMessageParams(
                    destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
                    operation='start_count',
                    payload=None,
                ),
                3.0,
            ),
            # finally, stop the counter one last time. "Count" in response will be approx. 4
            (
                IntersectClientMessageParams(
                    destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
                    operation='stop_count',
                    payload=None,
                ),
                3.0,
            ),
            # if you ran through all the messages, the counter value should be in the range of 3-6 .
        ]
        self.message_stack.reverse()

    def client_callback(
        self, source: str, operation: str, _has_error: bool, payload: Dict[str, Any]
    ) -> IntersectClientMessageParams:
        print('Source:', source)
        print('Operation:', operation)
        print('Payload:', payload)
        print()
        if not self.message_stack:
            # break out of pub/sub loop
            raise Exception
        message, wait_time = self.message_stack.pop()
        time.sleep(wait_time)
        return message


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
    config = IntersectClientConfig(
        **from_config_file,
    )
    # The counter will start after the initial message.
    # If the service is already active and counting, this may do nothing.
    initial_messages = [
        IntersectClientMessageParams(
            destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
            operation='start_count',
            payload=None,
        )
    ]
    orchestrator = SampleOrchestrator()
    client = IntersectClient(
        config=config,
        initial_messages=initial_messages,
        user_callback=orchestrator.client_callback,
    )
    default_intersect_lifecycle_loop(
        client,
    )

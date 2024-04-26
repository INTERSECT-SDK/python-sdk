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
        The message stack is a tuple: the message, and the time to wait before sending it.

        All approximations in comments come from the first run against the service, but the values can potentially vary
        if you run the client multiple times!
        """
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
        self, source: str, operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientMessageParams:
        """This simply prints the response from the Service to your console.

        In this case, we only send one message at a time, and will not send another message until we get a response back from the Service.
        If we have additional messages in our stack, we'll wait a little bit (based on the float value in the stack) before we
        send the next message to the Service.

        When we've exhausted our message stack, we just throw an Exception to break out of the pub/sub loop.

        Params:
          source: the source of the response message. In this case it will always be from the counting_service.
          operation: the name of the function we called in the original message. For example, since we call "start_count" in our first request,
            our first response will have "start_count" as the value.
          _has_error: Boolean value which represents an error. Since there is never an error in this example, it will always be "False".
          payload: Value of the response from the Service. The typing of the payload varies, based on the operation called and whether or not
            _has_error was set to "True". In this case, since we do not have an error, we can defer to the operation's response type. This response type is
            will be a dictionary resembling either "CountingServiceCapabilityImplementationState" or "CountingServiceCapabilityImplementationResponse",
            depending on the operation called.

            Note that the payload will always be a deserialized Python object, but the types are fairly limited: str, bool, float, int, None, List[T], and Dict[str, T]
            are the only types the payload can have. "T" in this case can be any of the 7 types just mentioned. Since both response types from the Service are
            classes*, this will be represented as a Dict[str, ...].

            *The only exception to the "Class gets deserialized to a dictionary" rule is if the class inherits from Python's NamedTuple builtin, in which case
            it will be deserialized as a List.
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

    # The counter will start after the initial message.
    # If the service is already active and counting, this may do nothing.
    initial_messages = [
        IntersectClientMessageParams(
            destination='counting-organization.counting-facility.counting-system.counting-subsystem.counting-service',
            operation='start_count',
            payload=None,
        )
    ]
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(messages_to_send=initial_messages),
        **from_config_file,
    )
    orchestrator = SampleOrchestrator()
    client = IntersectClient(
        config=config,
        user_callback=orchestrator.client_callback,
    )
    default_intersect_lifecycle_loop(
        client,
    )

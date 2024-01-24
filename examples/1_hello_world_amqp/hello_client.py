import logging
from typing import Any

from intersect_sdk import (
    IntersectClient,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)


def simple_client_callback(_source: str, _operation: str, _has_error: bool, payload: Any) -> None:
    """
    This simply prints the response from the service to your console.

    As we don't want to engage in a back-and-forth, we simply throw an exception to break out of the message loop.
    Ways to continue listening to messages or sending messages will be explored in other examples.
    """
    print(payload)
    # raise exception to break out of message loop - we only send and wait for one message
    raise Exception


if __name__ == '__main__':
    """
    step one: create configuration class, which handles user input validation - see the IntersectClientConfig class documentation for more info

    In most cases, everything under from_config_file should come from a configuration file, command line arguments, or environment variables.
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
                'port': 5672,
                'protocol': 'amqp0.9.1',
            },
        ],
    }
    config = IntersectClientConfig(
        **from_config_file,
    )

    """
    step two: construct the initial messages you want to send. In this case we will only send a single starting message.

    - The destination should match info.title in the service's schema. Another way to look at this is to see the service's
      HierarchyConfig, and then use
    - The operation should match one of the channels listed in the schema. In this case, 'say_hello_to_name' is the only
      operation exposed in the service.
    - The payload should represent what you want to send to the service's operation. You can determine the valid format
      from the service's schema. In this case, we're sending it a simple string. As long as the payload is a string,
      you'll get a message back.
    """
    initial_messages = [
        IntersectClientMessageParams(
            destination='hello-organization.hello-facility.hello-system.hello-subsystem.hello-service',
            operation='say_hello_to_name',
            payload='hello_client',
        )
    ]

    """
    step three: create the client.

    We also need a callback to handle incoming user messages.
    """
    client = IntersectClient(
        config=config,
        initial_messages=initial_messages,
        user_callback=simple_client_callback,
    )

    """
    step four - start lifecycle loop. The only necessary parameter is your client.
    with certain applications (i.e. REST APIs) you'll want to integrate the client in the existing lifecycle,
    instead of using this one.
    In that case, just be sure to call client.startup() and client.shutdown() at appropriate stages.
    """
    default_intersect_lifecycle_loop(
        client,
    )

    """
    When running the loop, you should have 'Hello, hello_client!' printed to your console.
    Note that the client will automatically exit.
    """

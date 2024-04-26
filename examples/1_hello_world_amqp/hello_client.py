import logging

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectClientMessageParams,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)


def simple_client_callback(
    _source: str, _operation: str, _has_error: bool, payload: INTERSECT_JSON_VALUE
) -> None:
    """This simply prints the response from the service to your console.

    As we don't want to engage in a back-and-forth, we simply throw an exception to break out of the message loop.
    Ways to continue listening to messages or sending messages will be explored in other examples.

    Params:
      _source: the source of the response message. In this case it will always be from the hello_service.
      _operation: the name of the function we called in the original message. In this case it will always be "say_hello_to_name".
      _has_error: Boolean value which represents an error. Since there is never an error in this example, it will always be "False".
      payload: Value of the response from the Service. The typing of the payload varies, based on the operation called and whether or not
        _has_error was set to "True". In this case, since we do not have an error, we can defer to the operation's response type. This response type is
        "str", so the type will be "str". The value will always be "Hello, hello_client!".

        Note that the payload will always be a deserialized Python object, but the types are fairly limited: str, bool, float, int, None, List[T], and Dict[str, T]
        are the only types the payload can have. "T" in this case can be any of the 7 types just mentioned.
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

    """
    step two: construct the initial messages you want to send. In this case we will only send a single starting message.

    - The destination should match info.title in the service's schema. Another way to look at this is to see the service's
      HierarchyConfig, and then write it as a single string: <ORGANIZATION>.<FACILITY>.<SYSTEM>.<SUBSYSTEM>.<SERVICE> .
      If you don't have a subsystem, use a "-" character instead.
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
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(messages_to_send=initial_messages),
        **from_config_file,
    )

    """
    step three: create the client.

    We also need a callback to handle incoming user messages.
    """
    client = IntersectClient(
        config=config,
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

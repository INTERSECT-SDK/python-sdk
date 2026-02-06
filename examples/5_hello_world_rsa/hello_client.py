"""
Hello World Client with RSA Encryption

This example demonstrates how to use RSA encryption when sending messages to INTERSECT services.
The client will encrypt requests using the service's public key and decrypt responses using its own private key.
"""

import time

from intersect_sdk import (
    HierarchyConfig,
    IntersectClient,
    IntersectServiceConfig,
)
from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams

"""
step one: create IntersectServiceConfig

Note: The client automatically generates an RSA key pair internally.
You don't need to manually create or manage encryption keys.
"""
config = IntersectServiceConfig(
    brokers=[
        {
            'username': 'intersect_username',
            'password': 'intersect_password',
            'port': 1883,
            'protocol': 'mqtt5.0',
        }
    ],
    hierarchy=HierarchyConfig(
        organization='hello-organization',
        facility='hello-facility',
        system='hello-system',
        subsystem='hello-subsystem-client',
        service='hello-client',
    ),
)

"""
step two: set up callback and then instantiate client
"""


def user_callback(source: str, operation: str, has_error: bool, payload: dict) -> None:
    if has_error:
        print(f'Error from {source}: {payload}')
    else:
        print(payload)


intersect_client = IntersectClient(
    config.hierarchy,
    config=config,
)

"""
step three: start up client with user callback
"""
intersect_client.startup(user_callback=user_callback)

"""
step four: send message with RSA encryption
Note the encryption_scheme='RSA' parameter
"""
message_params = IntersectDirectMessageParams(
    destination='hello-organization.hello-facility.hello-system.hello-subsystem.hello-service',
    operation='HelloExample.say_hello_to_name',
    payload='hello_client',
    encryption_scheme='RSA',  # Enable RSA encryption
)

intersect_client.send_message(message_params)
time.sleep(3)

"""
step five: shut down client
"""
intersect_client.shutdown()

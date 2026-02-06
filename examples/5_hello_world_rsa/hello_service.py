"""
Hello World Service with RSA Encryption

This example demonstrates how to use RSA encryption with INTERSECT services.
The service will encrypt responses to clients using the client's public key.
"""

import logging

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_message,
    intersect_status,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HelloServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """Capability implementation with RSA encryption support."""

    intersect_sdk_capability_name = 'HelloExample'

    @intersect_status()
    def status(self) -> str:
        """Basic status function which returns a hard-coded string."""
        return 'Up'

    @intersect_message()
    def say_hello_to_name(self, name: str) -> str:
        """Takes in a string parameter and says 'Hello' to the parameter!"""
        return f'Hello, {name}!'


if __name__ == '__main__':
    """
    Create a service with RSA encryption enabled.
    
    The service automatically generates an RSA key pair internally.
    When clients request RSA encryption, the service will:
    1. Fetch the client's public key
    2. Encrypt the response using the client's public key
    3. The client decrypts using its private key
    """
    
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt5.0',
            }
        ],
        'hierarchy': {
            'organization': 'hello-organization',
            'facility': 'hello-facility',
            'system': 'hello-system',
            'subsystem': 'hello-subsystem',
            'service': 'hello-service',
        },
    }

    config = IntersectServiceConfig(**from_config_file)

    """
    step two: create instances of your capabilities, which you will inject into the service
    """
    capabilities = [HelloServiceCapabilityImplementation()]

    """
    step three: create the service using your capability and configuration
    """
    intersect_service = IntersectService(capabilities, config)

    """
    step four: utilize the default_intersect_lifecycle_loop function to manage startup,
    the user lifecycle loop, and shutdown automatically. You must pass it the service
    and a function containing your optional lifecycle code to execute.
    """
    default_intersect_lifecycle_loop(intersect_service)

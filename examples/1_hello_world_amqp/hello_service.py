import logging

from intersect_sdk import (
    HierarchyConfig,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_message,
    intersect_status,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HelloServiceCapabilityImplementation:
    """
    Rudimentary capability implementation example.

    All capability implementations are required to have an @intersect_status decorated function,
    but we do not use it here.

    The operation we are calling is `say_hello_to_name` , so the message being sent will need to have
    an operationId of `say_hello_to_name`. The operation expects a string sent to it in the payload,
    and will send a string back in its own payload.
    """

    @intersect_status()
    def status(self) -> str:
        """
        Basic status function which returns a hard-coded string.
        """
        return 'Up'

    @intersect_message()
    def say_hello_to_name(self, name: str) -> str:
        """
        Takes in a string parameter and says 'Hello' to the parameter!
        """
        return f'Hello, {name}!'


if __name__ == '__main__':
    """
    step one: create configuration class, which handles validation - see the IntersectServiceConfig class documentation for more info

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
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='hello-organization',
            facility='hello-facility',
            system='hello-system',
            subsystem='hello-subsystem',
            service='hello-service',
        ),
        schema_version='0.0.1',
        **from_config_file,
    )

    """
    step two - create your own capability implementation class.

    You have complete control over how you construct this class, as long as it has decorated functions with
    @intersect_message and @intersect_status, and that these functions are appropriately type-annotated.
    """
    capability = HelloServiceCapabilityImplementation()

    """
    step three - create service from both the configuration and your own capability
    """
    service = IntersectService(capability, config)

    """
    step four - start lifecycle loop. The only necessary parameter is your service.
    with certain applications (i.e. REST APIs) you'll want to integrate the service in the existing lifecycle,
    instead of using this one.
    In that case, just be sure to call service.startup() and service.shutdown() at appropriate stages.
    """
    logger.info('Starting hello_service, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
    )

    """
    Note that the service will run forever until you explicitly kill the application (i.e. Ctrl+C)
    """

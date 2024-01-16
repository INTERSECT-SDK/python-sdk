# Standard imports
from sys import exit, stderr
from time import sleep

from definitions import capabilities
from intersect_sdk import (
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
    service,
)


class HelloWorldAdapter(service.IntersectService):
    def __init__(self, config: IntersectConfig):
        # Setup base class
        super().__init__(config)

        self.load_capabilities(capabilities)
        # Register request for "Hello, World!" message handler

        hello_world = self.get_capability('HelloWorld')
        self.register_interaction_handler(
            hello_world, hello_world.getInteraction('HelloRequest'), self.handle_hello_world_request
        )

    def handle_hello_world_request(self, message, args):
        print(
            f'Received request from {message.header.source}, sending reply...',
            flush=True,
        )
        self.invoke_interaction(
            self.get_capability('HelloWorld').getInteraction('HelloReply'),
            message.header.source,
            {'message': 'Hello, World!'},
        )
        return True


if __name__ == '__main__':
    # -- Config --
    config_dict = {
        'broker': {
            'username': 'intersect_username',
            'password': 'intersect_password',
            'host': '127.0.0.1',
            'port': 1883,
        },
        'hierarchy': {
            'organization': 'Oak Ridge National Laboratory',
            'facility': 'Hello World Facility',
            'system': 'Adapter',
            'subsystem': 'Adapter',
            'service': 'Adapter',
        },
    }

    try:
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    # -- Demo --
    adapter = HelloWorldAdapter(config)

    while not adapter.connection.broker_client.is_connected():
        print('Waiting to connect to broker...', flush=True)
        sleep(1.0)

    # Run until the process is killed externally
    print('Press Ctrl-C to exit:')
    try:
        while True:
            # Print the uptime every second.
            sleep(5.0)
            print(f'Adapter Uptime: {int(adapter.uptime)} seconds', flush=True)
    except KeyboardInterrupt:
        print('User requested exit')

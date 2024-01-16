# Standard importsDict
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from sys import exit, stderr
from time import sleep

from definitions import capabilities
from intersect_sdk import (
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_file,
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
        return True


def broker_config(config: dict):
    """
    Edit the default host and port for the broker configuration.
    """
    config['broker']['host'] = '127.0.0.1'
    config['broker']['port'] = 1883


if __name__ == '__main__':
    # -- Arguments --
    parser = ArgumentParser(
        description='Hello world adapter',
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--config',
        type=Path,
        default='config-adapter.yml',
        help='Path to config file',
    )
    args = parser.parse_args()

    # -- Config --
    try:
        config = load_config_from_file(args.config, broker_config)
    except IntersectConfigParseException as ex:
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

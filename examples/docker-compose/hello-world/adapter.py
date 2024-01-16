# Standard importsDict
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from pathlib import Path
from sys import exit, stderr
from time import sleep

# intersect imports
from intersect_sdk import IntersectConfig, adapter, config_functions, exceptions, messages


class HelloWorldAdapter(adapter.Adapter):
    def __init__(self, config: IntersectConfig):
        # Setup base class
        super().__init__(config)

        # Register request for "Hello, World!" message handler
        self.register_message_handler(
            self.handle_hello_world_request, {messages.Request: [messages.Request.DETAIL]}
        )

    def handle_hello_world_request(self, message, type_, subtype, payload):
        print(f'Received request from {message.header.source}, sending reply...', flush=True)
        reply = self.generate_status_general(detail={'message': 'Hello, World!'})
        reply.header.destination = message.header.source
        self.send(reply)
        return True


if __name__ == '__main__':
    # -- Arguments --
    parser = ArgumentParser(
        description='hello-world-requestor',
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
        config = config_functions.load_config_from_file(args.config)
    except exceptions.IntersectConfigParseException as ex:
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
        adapter.start_status_ticker()
        while True:
            # Print the uptime every second.
            sleep(5.0)
            print(f'Adapter Uptime: {int(adapter.uptime)} seconds', flush=True)
    except KeyboardInterrupt:
        print('User requested exit')

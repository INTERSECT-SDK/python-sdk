# Standard imports
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from os import environ
from pathlib import Path
from sys import exit, stderr
from time import sleep

from intersect_sdk import (
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_file,
    service
)
from definitions import capabilities

class HelloWorldRequestor(service.IntersectService):
    def __init__(self, config: IntersectConfig):
        # Setup base class
        super().__init__(config)

        self.load_capabilities(capabilities)
        # Register request for "Hello, World!" message handler
        hello_world = self.get_capability("HelloWorld")
        self.register_interaction_handler(hello_world, hello_world.getInteraction("HelloReply"), self.handle_hello_world_reply)

    def send_request_to_hello_world_adapter(self, destination: str):
        self.invoke_interaction(self.get_capability("HelloWorld").getInteraction("HelloRequest"), destination, {})

    def handle_hello_world_reply(self, message, args):
        print("Reply from Hello World Adapter:", flush=True)
        print(args["payload"], flush=True)
        return True


def broker_config(config: dict):
    """
    Edit the default host and port for the broker configuration.
    """
    config["broker"]["host"] = "127.0.0.1"
    config["broker"]["port"] = 1883


if __name__ == "__main__":
    # -- Arguments --
    parser = ArgumentParser(
        description="Hello world requestor",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default="config-requestor.yml",
        help="Path to config file",
    )

    parser.add_argument(
        "--destination",
        type=str,
        default=environ.get("DESTINATION", "Adapter"),
        help="System name of the destination for the request",
    )
    args = parser.parse_args()

    # -- Config --
    try:
        config = load_config_from_file(args.config, broker_config)
    except IntersectConfigParseException as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    # -- Demo --
    requestor = HelloWorldRequestor(config)

    while not requestor.connection.broker_client.is_connected():
        print("Waiting to connect to message broker...", flush=True)
        sleep(1.0)

    # Run until the process is killed externally
    print("Press Ctrl-C to exit:")
    try:
        # send request message to hello-world adapter
        delay_seconds = 5
        print(f"Requestor will send request in {delay_seconds} seconds...", flush=True)
        sleep(delay_seconds)
        requestor.send_request_to_hello_world_adapter(args.destination)
        print("Request sent!", flush=True)
        while True:
            # Print the uptime every second.
            sleep(5.0)
            print(f"Requestor Uptime: {int(requestor.uptime)} seconds", flush=True)
    except KeyboardInterrupt:
        print("User requested exit")

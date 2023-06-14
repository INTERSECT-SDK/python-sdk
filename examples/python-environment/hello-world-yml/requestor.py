# Standard imports
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from os import environ
from pathlib import Path
from time import sleep
from sys import exit, stderr

from intersect import (
    Adapter,
    IntersectConfig,
    load_config_from_file,
    IntersectConfigParseException,
    messages,
)


class HelloWorldRequestor(Adapter):
    def __init__(self, config: IntersectConfig):

        # Setup base class
        super().__init__(config)

        # Register request for "Hello, World!" message handler
        self.register_message_handler(
            self.handle_hello_world_reply,
            {messages.Status: [messages.Status.GENERAL]}
        )

    def send_request_to_hello_world_adapter(self, destination: str):
        # Subscribe to the hello world adapter reply channel
        reply_channel = self.connection.channel(f"{destination}/reply")
        reply_channel.subscribe(self.resolve_status_receive)

        # Create and send the message to the hello world adapter
        request = self.generate_request_detail(
            destination=destination,
            arguments={},
        )
        self.send(request)

    def handle_hello_world_reply(self, message, type_, subtype, payload):
        print("Reply from Hello World Adapter:", flush=True)
        print(message.detail, flush=True)
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

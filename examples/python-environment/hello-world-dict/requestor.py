# Standard imports
from sys import exit, stderr
from time import sleep

from intersect_sdk import (
    Adapter,
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
    messages,
)


class HelloWorldRequestor(Adapter):
    def __init__(self, config: IntersectConfig):
        # Setup base class
        super().__init__(config)

        # Register request for "Hello, World!" message handler
        self.register_message_handler(
            self.handle_hello_world_reply, {messages.Status: [messages.Status.GENERAL]}
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


if __name__ == "__main__":
    # -- Config --
    config_dict = {
        "broker": {
            "username": "intersect_username",
            "password": "intersect_password",
            "host": "127.0.0.1",
            "port": 1883,
        },
        "hierarchy": {
            "organization": "Oak Ridge National Laboratory",
            "facility": "Hello World Facility",
            "system": "Requestor",
            "subsystem": "Requestor",
            "service": "Requestor",
        },
        "destination": "Adapter",
    }

    try:
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
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
        requestor.send_request_to_hello_world_adapter(config_dict["destination"])
        print("Request sent!", flush=True)
        while True:
            # Print the uptime every second.
            sleep(5.0)
            print(f"Requestor Uptime: {int(requestor.uptime)} seconds", flush=True)
    except KeyboardInterrupt:
        print("User requested exit")

import time
from sys import exit, stderr
from typing import Tuple

from intersect import common, messages


class Client(common.Adapter):
    arguments_parser: str = "json"
    status_ticker_interval: float = 30.0
    id_counter_init: int = 100
    handled_status: Tuple = (messages.Status.GENERAL,)

    def __init__(self, config: common.IntersectConfig):
        super().__init__(config)

        self.register_message_handler(
            self.handle_status_general,
            {messages.Status: [messages.Status.GENERAL]},
        )

        # Generate and publish start message
        self.status_channel.publish(self.generate_status_starting())

        # Start status ticker and start action subscribe
        self.start_status_ticker()

    def handle_status_general(self, message, type_, subtype, payload):
        print("Count received from server: {}".format(payload["count"]))
        print(
            f"Received request from {message.header.source}, sending reply...",
            flush=True,
        )
        reply = self.generate_status_general(detail={"message": "Hello from client"})
        reply.header.destination = message.header.source
        self.send(reply)
        return True

    def generate_request(self, destination):
        msg = self.generate_request_detail(destination, dict())
        self.connection.channel(destination + "/request").publish(msg)

    def generate_stop(self, destination):
        msg = self.generate_action_stop(destination, dict())
        self.send(msg)

    def generate_start(self, destination):
        msg = self.generate_action_start(destination, dict())
        self.send(msg)


if __name__ == "__main__":
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
            "system": "Example Client",
            "subsystem": "Example Client",
            "service": "example-client",
        },
    }

    try:
        config = common.load_config_from_dict(config_dict)
    except common.IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    client = Client(config)

    print("Press Ctrl-C to exit.")

    try:
        while True:
            time.sleep(1)
            print(f"Uptime: {client.uptime}", end="\r")
            client.generate_request("example-server")
            client.generate_stop("example-server")
            time.sleep(5)
            client.generate_request("example-server")
            client.generate_start("example-server")
            time.sleep(5)
            client.generate_request("example-server")
    except KeyboardInterrupt:
        print("\nUser requested exit.")

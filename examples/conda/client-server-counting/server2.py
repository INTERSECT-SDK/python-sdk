import time
from sys import exit, stderr

from intersect import common
from intersect import messages


class CountingAdapter(common.Adapter):

    def __init__(self, config: common.IntersectConfig):
        # Setup base class
        super().__init__(config)

        # Register request for "Hello, World!" message handler
        self.register_message_handler(
            self.handle_counting_request,
            {messages.Request: [messages.Request.DETAIL]},
        )

    def handle_counting_request(self, message, type_, subtype, payload):
        print(
            f"Received request from {message.header.source}, sending reply...",
            flush=True,
        )
        reply = self.generate_status_general(detail={"message": "Hello counter"})
        reply.header.destination = message.header.source
        self.send(reply)
        return True


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
            "system": "Adapter",
            "subsystem": "Adapter",
            "service": "Adapter",
        },
    }

    try:
        config = common.load_config_from_dict(config_dict)
    except common.IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    counting_adapter = CountingAdapter(config)
    counting_adapter.start_status_ticker()

    print("Press Ctrl-C to exit.")

    try:
        while True:
            time.sleep(5)
            print(f"Uptime: {counting_adapter.uptime}", end="\r")
    except KeyboardInterrupt:
        print("\nUser requested exit.")

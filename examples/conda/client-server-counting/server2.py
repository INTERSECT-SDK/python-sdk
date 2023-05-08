import time
import threading
from sys import exit, stderr
from typing import Union

from intersect import common
from intersect import messages


class CountingAdapter(common.Adapter):

    def __init__(self, config: common.IntersectConfig):
        super().__init__(config)

        # Set attributes for counting
        self.counter_thread: Union[None, threading.Thread] = None
        self.count_active: bool = True

        # Register message handlers
        self.register_message_handler(
            self.handle_start,
            {messages.Action: [messages.Action.START, messages.Action.RESTART]}
        )

        self.register_message_handler(
            self.handle_stop,
            {messages.Action: [messages.Action.STOP]}
        )

        self.register_message_handler(
            self.handle_request_detail,
            {messages.Request: [messages.Request.DETAIL]}
        )

        # Start status ticker and start action subscribe
        self.start_status_ticker()

        # Initialize the count to 0
        self.count = 0

    def handle_start(self, message, type_, subtype, payload):
        self.restart_count()
        return True

    def handle_stop(self, message, type_, subtype, payload):
        self.stop_count()
        return True

    def handle_request_detail(self, message, type_, subtype, payload):
        print(
            f"Received request from {message.header.source}, sending reply...",
            flush=True,
        )
        reply = self.generate_status_general(detail={"count": self.count})
        reply.header.destination = message.header.source
        self.send(reply)
        return True

    def _run_count(self):
        while self.count_active:
            self.count += 1
            time.sleep(1.0)

    def start_count(self):
        if self.counter_thread is None:
            self.counter_thread = threading.Thread(
                target=self._run_count,
                daemon=True,
                name=f"{self.service_name}_counter_thread"
            )
            self.counter_thread.start()

    def stop_count(self):
        if self.counter_thread is not None:
            self.count_active = False
            self.counter_thread.join()
            self.counter_thread = None
            self.count_active = True

    def restart_count(self):
        if self.counter_thread is not None:
            self.stop_count()
        self.start_count()


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
            "system": "Example Server",
            "subsystem": "Example Server",
            "service": "example-server",
        },
    }

    try:
        config = common.load_config_from_dict(config_dict)
    except common.IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    counting_adapter = CountingAdapter(config)
    counting_adapter.start_count()

    print("Press Ctrl-C to exit.")

    try:
        while True:
            time.sleep(5)
            print(f"Uptime: {counting_adapter.uptime}", end="\r")
    except KeyboardInterrupt:
        print("\nUser requested exit.")

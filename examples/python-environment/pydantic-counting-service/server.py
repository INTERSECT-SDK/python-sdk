import threading
import time
from sys import exit, stderr
from typing import Optional

from intersect_sdk import (
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
    service
)

from definitions import (
    StatusInteraction,
    StartInteraction,
    StopInteraction,
    RestartInteraction,
    DetailInteraction)


class CountingAdapter(service.IntersectService):

    def __init__(self, config: IntersectConfig):
        super().__init__(config)

        # Set attributes for counting
        self.counter_thread: Optional[threading.Thread] = None
        self.count_active: bool = True

        # Register interaction handlers
        self.add_interaction("counter", StartInteraction(), self.handle_start)
        self.add_interaction("counter", StopInteraction(), self.handle_stop)
        self.add_interaction("counter", RestartInteraction(), self.handle_start)
        self.add_interaction("counter", DetailInteraction(), self.handle_request_detail)

        # Initialize the count to 0
        self.count = 0

    def handle_start(self, message, payload):
        print("Received start request.")
        self.restart_count()
        return True

    def handle_stop(self, message, payload):
        print("Received stop request.")
        self.stop_count()
        return True

    def handle_request_detail(self, message, payload):
        print(
            f"Received request from {message.header.source}, sending reply...",
            flush=True,
        )
        self.invoke_interaction(StatusInteraction(), message.header.source, {"count": self.count})
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
                name=f"{self.service_name}_counter_thread",
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
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
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

import time
from sys import exit, stderr

from intersect_sdk import (
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
    service
)

from definitions import capabilities

class Client(service.IntersectService):
    arguments_parser: str = "json"
    status_ticker_interval: float = 30.0
    id_counter_init: int = 100

    def __init__(self, config: IntersectConfig):
        super().__init__(config)
        self.load_capabilities(capabilities)

        counting_capability = self.get_capability("Counting")
        self.register_interaction_handler(counting_capability, counting_capability.getInteraction("Status"), self.handle_status_general)

    def handle_status_general(self, message, args):
        print("Count received from server: {}".format(args['payload']))
        return True

    def generate_request(self, destination):
        self.invoke_interaction(self.get_capability("Counting").getInteraction("Detail"), destination, None)

    def generate_stop(self, destination):
        self.invoke_interaction(self.get_capability("Counting").getInteraction("Stop"), destination, None)

    def generate_start(self, destination):
        self.invoke_interaction(self.get_capability("Counting").getInteraction("Start"), destination, None)



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
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
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

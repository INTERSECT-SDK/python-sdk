from sys import exit, stderr
from time import sleep

from intersect import Adapter, IntersectConfig, IntersectConfigParseException, load_config_from_dict


class StatusPublisherAdapter(Adapter):
    def __init__(self, config: IntersectConfig):
        # Setup base class
        super().__init__(config)

        # Generate and publish start message
        self.send(self.generate_status_starting())

        # Start status ticker and start action subscribe
        self.start_status_ticker()


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
            "facility": "Inspecting Messages Facility",
            "system": "Publisher",
            "subsystem": "Publisher",
            "service": "Publisher",
        },
    }

    try:
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    # -- Demo --
    adapter = StatusPublisherAdapter(config)

    # Run until the process is killed externally
    print("Press Ctrl-C to exit:")
    try:
        adapter.start_status_ticker()
        while True:
            # Print the uptime every second.
            sleep(5.0)
            print(f"Publisher Uptime: {int(adapter.uptime)} seconds", flush=True)
    except KeyboardInterrupt:
        print("User requested exit")

import os
import time

from intersect import common


class StatusPublisherAdapter(common.Adapter):
    def __init__(self,
                 system_name: str,
                 broker_address: str,
                 broker_port: int,
                 username: str,
                 password: str):

        # Setup base class
        super().__init__(system_name, broker_address, broker_port, username, password)

        # Generate and publish start message
        self.send(self.generate_start_status())

        # Start status ticker and start action subscribe
        self.start_status_ticker()


if __name__ == "__main__":
    # -- Arguments and logging --
    system_name = os.environ.get("SYSTEM_NAME", "status-publisher")
    parser = common.setup_parser(system_name=system_name)
    args = parser.parse_args()
    common.setup_logging(args)

    # -- Demo --
    adapter = StatusPublisherAdapter(
        args.system_name,
        args.broker_address,
        args.broker_port,
        args.broker_username,
        args.broker_password
    )

    # Run until the process is killed externally
    print("Press Ctrl-C to exit:")
    try:
        while True:
            # Print the uptime every second.
            time.sleep(float(os.environ.get("UPTIME_INTERVAL", 5.0)))
            print(f"{system_name} uptime: {int(adapter.uptime)} seconds", flush=True)
    except KeyboardInterrupt:
        print("User requested exit")

import os
import time

from intersect import messages
from intersect import common


class MessageInspectorAdapter(common.Adapter):
    def __init__(self,
                 system_name: str,
                 broker_address: str,
                 broker_port: int,
                 username: str,
                 password: str):

        # Setup base class
        super().__init__(system_name, broker_address, broker_port, username, password)

        # Set up channel that listens to other status messages via wildcard topic
        self.connection.broker_client._connection.message_callback_add(
            "+/status",
            self.inspect_messages,
        )
        self.connection.broker_client._connection.subscribe([("+/status", 0)])

        self.connection.broker_client._connection.loop_start()

        # Generate and publish start message
        self.send(self.generate_start_status())

        # Start status ticker and start action subscribe
        self.start_status_ticker()

    @staticmethod
    def inspect_messages(client, userdata, message):
        payload = messages.deserialize(message.payload)
        print(payload)
        return True


if __name__ == "__main__":
    # -- Arguments and logging --
    system_name = os.environ.get("SYSTEM_NAME", "message-inspector")
    parser = common.setup_parser(system_name=system_name)
    args = parser.parse_args()
    common.setup_logging(args)

    # -- Demo --
    adapter = MessageInspectorAdapter(
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

from time import sleep
from sys import exit, stderr

from intersect import (
    Adapter,
    IntersectConfig,
    load_config_from_dict,
    IntersectConfigParseException,
    messages,
)


class MessageInspectorAdapter(Adapter):
    def __init__(self, config: IntersectConfig):
        # Setup base class
        super().__init__(config)

        # Set up channel that listens to other status messages via wildcard topic
        self.connection.broker_client._connection.message_callback_add(
            "+/status",
            self.inspect_messages,
        )
        self.connection.broker_client._connection.subscribe([("+/status", 0)])

        self.connection.broker_client._connection.loop_start()

        # Generate and publish start message
        self.send(self.generate_status_starting())

        # Start status ticker and start action subscribe
        self.start_status_ticker()

    @staticmethod
    def inspect_messages(client, userdata, message):
        json_handler = messages.JsonHandler()
        payload = json_handler.deserialize(message.payload)
        print(payload)
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
            "facility": "Inspecting Messages Facility",
            "system": "Inspector",
            "subsystem": "Inspector",
            "service": "Inspector",
        },
    }

    try:
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    # -- Demo --
    adapter = MessageInspectorAdapter(config)

    while not adapter.connection.broker_client.is_connected():
        print("Waiting to connect to broker...", flush=True)
        sleep(1.0)

    # Run until the process is killed externally
    print("Press Ctrl-C to exit:")
    try:
        adapter.start_status_ticker()
        while True:
            # Print the uptime every second.
            sleep(5.0)
            print(f"Inspector Uptime: {int(adapter.uptime)} seconds", flush=True)
    except KeyboardInterrupt:
        print("User requested exit")

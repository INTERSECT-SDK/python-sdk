import json
import time
from sys import exit, stderr
from typing import Tuple

import custom_microscopy_messages

from intersect_sdk import (
    Adapter,
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
    messages,
)


class MicroscopyCustomMessageAdapter(Adapter):

    def __init__(self, config: IntersectConfig):
        super().__init__(config)

        # Register message handlers
        self.register_message_handler(
            self.handle_start,
            {messages.Action: [messages.Action.START, messages.Action.RESTART]},
        )
        custom_microscopy_messages.CustomMicroscopyMessages.load_schema()
        custom_microscopy_messages.CustomMicroscopyMessages.check_schema()

    def handle_start(self, message, type_, subtype, payload):
        arguments = json.loads(message.arguments)
        if not custom_microscopy_messages.CustomMicroscopyMessages.is_valid(arguments):
            print("Received invalid message.")
        else:
            if "EM_Activity" in arguments:
                print("EM Activity message received")
            if "SystemStatus" in arguments:
                print("SystemStatus message received")
        print(arguments)
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

    adapter = MicroscopyCustomMessageAdapter(config)

    print("Press Ctrl-C to exit.")

    try:
        while True:
            time.sleep(5)
            print(f"Uptime: {adapter.uptime}", end="\r")
    except KeyboardInterrupt:
        print("\nUser requested exit.")

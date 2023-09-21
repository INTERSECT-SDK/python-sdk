import json
import time
from sys import exit, stderr

from jsonschema import ValidationError

from intersect_sdk import (
    Adapter,
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
)
from intersect_sdk.messages import schema_handler

good_em_activity_msg = {
    "EM_Activity": {
        "Header": {
            "SystemID": {"UUID": "lmnop"},
            "Timestamp": "2023-08-15T20:20:39+00:00",
            "SchemaVersion": "1",
        },
        "MessageState": "NEW",
        "MessageData": {
            "SubsystemID": {"UUID": "1234abcd"},
            "Activity": [
                {
                    "Repetition": {
                        "Periodic": {"RepetitionInterval": "Never"},
                        "Finite": {"RepetitionAttempts": 0},
                        "Continuous": {"RepetitionInterval": "Never"},
                    },
                    "ConsentRequired": False,
                    "ConsentState": "INITIAL",
                    "ActivityID": {"UUID": "xyz"},
                    "CapabilityID": {"UUID": "xyz"},
                    "ActivityRank": {"Precedence": 2, "Priority": 4},
                    "Interactive": False,
                    "ActivityState": "DISABLED",
                }
            ],
        },
    }
}

good_system_status_msg = {
    "SystemStatus": {
        "Header": {
            "SystemID": {"UUID": "lmnop"},
            "Timestamp": "2023-08-15T20:20:39+00:00",
            "SchemaVersion": "1",
        },
        "MessageState": "NEW",
        "MessageData": {"SystemID": {"UUID": "abc123"}, "SystemState": "OPERATIONAL"},
    }
}

good_multi_msg = {
    "EM_Activity": {
        "Header": {
            "SystemID": {"UUID": "lmnop"},
            "Timestamp": "2023-08-15T20:20:39+00:00",
            "SchemaVersion": "1",
        },
        "MessageState": "NEW",
        "MessageData": {
            "SubsystemID": {"UUID": "1234abcd"},
            "Activity": [
                {
                    "Repetition": {
                        "Periodic": {"RepetitionInterval": "Never"},
                        "Finite": {"RepetitionAttempts": 0},
                        "Continuous": {"RepetitionInterval": "Never"},
                    },
                    "ConsentRequired": False,
                    "ConsentState": "INITIAL",
                    "ActivityID": {"UUID": "xyz"},
                    "CapabilityID": {"UUID": "xyz"},
                    "ActivityRank": {"Precedence": 2, "Priority": 4},
                    "Interactive": False,
                    "ActivityState": "DISABLED",
                }
            ],
        },
    },
    "SystemStatus": {
        "Header": {
            "SystemID": {"UUID": "lmnop"},
            "Timestamp": "2023-08-15T20:20:39+00:00",
            "SchemaVersion": "1",
        },
        "MessageState": "NEW",
        "MessageData": {"SystemID": {"UUID": "abc123"}, "SystemState": "OPERATIONAL"},
    },
}

bad_system_status_msg = {
    "SystemStatus": {
        "Header": {
            "SystemID": {"UUID": "lmnop"},
            "Timestamp": "2023-08-15T20:20:39+00:00",
            "SchemaVersion": "1",
        },
        "MessageState": "NEWs",
        "MessageData": {"SystemID": {"UUID": "abc123"}, "SystemState": "OPERATIONAL"},
    }
}


class Client(Adapter):
    def __init__(self, config: IntersectConfig):
        super().__init__(config)

        # Generate and publish start message
        self.status_channel.publish(self.generate_status_starting())

    with open('./FSI_MessagingStandard.json') as schemaf:
        schemaHandler = schema_handler.SchemaHandler(json.loads('\n'.join(schemaf.readlines())))

    def send_message(self, destination, msg):
        try:
            self.send(self.generate_custom_message(destination, msg, self.schemaHandler))
        except ValidationError:
            print("Sending message failed due to validation.")

    def send_message_no_validate(self, destination, msg):
        m = self.generate_action_start(destination, msg)
        self.send(m)


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
            print("Sending an EM activity message.")
            client.send_message("example-server", good_em_activity_msg)
            time.sleep(8)
            print("Sending a System Status message.")
            client.send_message("example-server", good_system_status_msg)
            time.sleep(8)
            print("Sending both a EM and System status message at once.")
            client.send_message("example-server", good_multi_msg)
            time.sleep(8)
            print("Sending a bad System status message and failing.")
            try:
                client.send_message("example-server", bad_system_status_msg)
            except ValidationError:
                print("message failed to validate")
            time.sleep(8)
            print("Being a bad user and forcing a bad message through without validation.")
            client.send_message_no_validate("example-server", bad_system_status_msg)
            time.sleep(20)
    except KeyboardInterrupt:
        print("\nUser requested exit.")

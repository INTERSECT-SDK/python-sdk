import json
import time
from sys import exit, stderr

from intersect_sdk import (
    Adapter,
    IntersectConfig,
    IntersectConfigParseException,
    load_config_from_dict,
)
from intersect_sdk.messages import Custom, schema_handler


class MicroscopyCustomMessageAdapter(Adapter):
    def __init__(self, config: IntersectConfig):
        super().__init__(config)

        with open('./FSI_MessagingStandard.json') as schemaf:
            schema = json.loads('\n'.join(schemaf.readlines()))

        # Register message handlers
        self.register_message_handler(
            self.handle_all_custom_messages,
            {Custom: [Custom.ALL]},
            schema_handler.SchemaHandler(schema),
        )

        self.register_message_handler(
            self.handle_em_activity_messages,
            {Custom: [Custom.ALL]},
            schema_handler.SchemaHandler(schema, screen='EM_Activity'),
        )

        self.register_message_handler(
            self.handle_system_status_messages,
            {Custom: [Custom.ALL]},
            schema_handler.SchemaHandler(schema, screen='SystemStatus'),
        )

    def handle_all_custom_messages(self, message, type_, subtype, payload):
        print('Custom message received')

    def handle_em_activity_messages(self, message, type_, subtype, payload):
        print('em activity message received')
        print(payload)

    def handle_system_status_messages(self, message, type_, subtype, payload):
        print('system status message received')
        print(payload)


if __name__ == '__main__':
    config_dict = {
        'broker': {
            'username': 'intersect_username',
            'password': 'intersect_password',
            'host': '127.0.0.1',
            'port': 1883,
        },
        'hierarchy': {
            'organization': 'Oak Ridge National Laboratory',
            'facility': 'Hello World Facility',
            'system': 'Example Server',
            'subsystem': 'Example Server',
            'service': 'example-server',
        },
    }

    try:
        config = load_config_from_dict(config_dict)
    except IntersectConfigParseException() as ex:
        print(ex.message, file=stderr)
        exit(ex.returnCode)

    adapter = MicroscopyCustomMessageAdapter(config)

    print('Press Ctrl-C to exit.')

    try:
        while True:
            time.sleep(5)
            print(f'Uptime: {adapter.uptime}', end='\r')
    except KeyboardInterrupt:
        print('\nUser requested exit.')

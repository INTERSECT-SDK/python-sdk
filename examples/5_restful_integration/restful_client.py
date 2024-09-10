import logging

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)

RESTFUL_SERVICE = 'restful-organization.restful-facility.restful-system.restful-subsystem.restful-service'

class EventListener:
    def event_callback(
        self, _source: str, _operation: str, event_name: str, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        print(payload)

if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }

    # we initially only listen for ping service events,
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            services_to_start_listening_for_events=[
                RESTFUL_SERVICE,
            ]
        ),
        **from_config_file,
    )
    orchestrator = EventListener()
    client = IntersectClient(
        config=config,
        event_callback=orchestrator.event_callback,
    )
    default_intersect_lifecycle_loop(
        client,
    )
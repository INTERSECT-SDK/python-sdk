import logging

from intersect_sdk import (
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    default_intersect_lifecycle_loop,
)

logging.basicConfig(level=logging.INFO)
logging.getLogger('pika').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

PING_SERVICE = 'p-ng-organization.p-ng-facility.p-ng-system.p-ng-subsystem.ping-service'
PONG_SERVICE = 'p-ng-organization.p-ng-facility.p-ng-system.p-ng-subsystem.pong-service'


class SampleOrchestrator:
    """Basic orchestrator with an event callback.

    The event callback switches between listening to 'ping' and 'pong' events; it never listens to both simultaneously.
    """

    MAX_EVENTS_TO_PROCESS = 4

    def __init__(self) -> None:
        """Straightforward constructor, just initializes global variable which counts events."""
        self.events_encountered = 0

    def event_callback(
        self, _source: str, _operation: str, event_name: str, payload: INTERSECT_JSON_VALUE
    ) -> IntersectClientCallback:
        """Handles events from two Services at once.

        With this handler, the order of instructions goes like this:

        1. Listen for a ping event.
        2. On ping event - Start listening for pong events and stop listening for ping events.
        3. On pong event - Start listening for ping events and stop listening for pong events.
        4. Repeat steps 2-3 until we have processed the maximum number of events we want to.
        """
        self.events_encountered += 1
        logger.info(payload)
        print(payload)
        if self.events_encountered == self.MAX_EVENTS_TO_PROCESS:
            raise Exception

        # we would normally also check the source here. With certain services, checking the operation can also be helpful.
        if event_name == 'ping':
            return IntersectClientCallback(
                services_to_start_listening_for_events=[PONG_SERVICE],
                services_to_stop_listening_for_events=[PING_SERVICE],
            )
        return IntersectClientCallback(
            services_to_start_listening_for_events=[PING_SERVICE],
            services_to_stop_listening_for_events=[PONG_SERVICE],
        )


if __name__ == '__main__':
    from_config_file = {
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 5672,
                'protocol': 'amqp0.9.1',
            },
        ],
    }

    # we initially only listen for ping service events,
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            services_to_start_listening_for_events=[
                PING_SERVICE,
            ]
        ),
        **from_config_file,
    )
    orchestrator = SampleOrchestrator()
    client = IntersectClient(
        config=config,
        event_callback=orchestrator.event_callback,
    )
    default_intersect_lifecycle_loop(
        client,
    )

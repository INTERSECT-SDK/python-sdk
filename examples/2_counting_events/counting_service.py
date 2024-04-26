import logging
import threading
import time

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_event,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CountingServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """This example is meant to showcase a simple event emitter.

    This service does not have any endpoints, but simply fires off a single event every three seconds.
    """

    def after_service_startup(self) -> None:
        """This is a 'post-initialization' method.

        We want to call it AFTER we start up the Service. Until that point, we DON'T want to emit any events.
        """
        self.counter = 1
        self.counter_thread = threading.Thread(
            target=self.increment_counter_function,
            daemon=True,
            name='counter_thread',
        )
        self.counter_thread.start()

    @intersect_event(events={'increment_counter': IntersectEventDefinition(event_type=int)})
    def increment_counter_function(self) -> None:
        """This is the event thread which continually emits count events.

        Every 3 seconds, we fire off a new 'increment_counter' event; each time, we are firing off a value 3 times greater than before.

        We have to configure our event on the @intersect_event decorator. Since 'increment_counter' is emitting an integer value,
        we need to specify the emission type on the decorator. Failure to register the event and its type will mean that the event won't
        be emitted.
        """
        while True:
            time.sleep(2.0)
            self.counter *= 3
            self.intersect_sdk_emit_event('increment_counter', self.counter)


if __name__ == '__main__':
    from_config_file = {
        'data_stores': {
            'minio': [
                {
                    'username': 'AKIAIOSFODNN7EXAMPLE',
                    'password': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
                    'port': 9000,
                },
            ],
        },
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
    }
    config = IntersectServiceConfig(
        hierarchy=HierarchyConfig(
            organization='counting-organization',
            facility='counting-facility',
            system='counting-system',
            subsystem='counting-subsystem',
            service='counting-service',
        ),
        status_interval=30.0,
        **from_config_file,
    )
    capability = CountingServiceCapabilityImplementation()
    service = IntersectService(capability, config)
    logger.info('Starting counting_service, use Ctrl+C to exit.')

    """
    Here, we provide the after_service_startup function on the capability as a post startup callback.

    This ensures we don't emit any events until we've actually started up our Service.
    """
    default_intersect_lifecycle_loop(
        service, post_startup_callback=capability.after_service_startup
    )

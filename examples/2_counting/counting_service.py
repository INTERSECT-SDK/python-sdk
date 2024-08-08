import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    IntersectServiceConfig,
    default_intersect_lifecycle_loop,
    intersect_message,
    intersect_status,
)
from pydantic import BaseModel, Field
from typing_extensions import Annotated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CountingServiceCapabilityImplementationState(BaseModel):
    """We can't just use any class to represent state. This class either needs to extend Pydantic's BaseModel class, or be a dataclass. Both the Python standard library's dataclass and Pydantic's dataclass are valid."""

    count: Annotated[int, Field(default=0, ge=0)]
    """
    Generic integer state - increases/decreases as needed

    Note the annotations - this advertises to the schema that the default value is 0,
    and that the value should always be greater than or equal to 0.
    """
    counting: bool = False
    """
    True if the count thread is running, False if it's not
    """


@dataclass
class CountingServiceCapabilityImplementationResponse:
    """This class is used as a reply to messages which may not do anything.

    It's also an example of using a dataclass instead of Pydantic's BaseModel.
    """

    state: CountingServiceCapabilityImplementationState
    """
    We wrap the state in the response
    """
    success: bool
    """
    If true: message caused a change. If false: it did not.
    """


class CountingServiceCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """This example is meant to showcase that your implementation is able to track state if you want it to.

    Please note that this is not an especially robust implementation, as in the instance
    the service gets two messages at the same time, it may manage to create
    two threads at once.
    """

    def __init__(self) -> None:
        """Constructors are never exposed to INTERSECT.

        You are free to provide whatever parameters you like to the constructor, and
        do whatever you like in the constructor. In this instance, we just initialize our state.
        """
        super().__init__()
        self.state = CountingServiceCapabilityImplementationState()
        self.counter_thread: Optional[threading.Thread] = None

    @intersect_status()
    def status(self) -> CountingServiceCapabilityImplementationState:
        """Basic status function communicates our current state.

        We set the status interval in the configuration to be 30 seconds long - if you
        run the service without the client, and set the log level
        of intersect-sdk to DEBUG, then you'll be able to see the message
        every 30 seconds in your terminal. (By default, this value is 5 minutes.)
        """
        return self.state

    @intersect_message()
    def start_count(self) -> CountingServiceCapabilityImplementationResponse:
        """Start the counter (potentially from any number). "Fails" if the counter is already running.

        Returns:
          A CountingServiceCapabilityImplementationResponse object. The success value will be:
            True - if counter was started successfully
            False - if counter was already running and this was called
        """
        if self.state.counting:
            return CountingServiceCapabilityImplementationResponse(
                state=self.state,
                success=False,
            )
        self.state.counting = True
        self.counter_thread = threading.Thread(
            target=self._run_count,
            daemon=True,
            name='counter_thread',
        )
        self.counter_thread.start()
        return CountingServiceCapabilityImplementationResponse(
            state=self.state,
            success=True,
        )

    @intersect_message()
    def stop_count(self) -> CountingServiceCapabilityImplementationResponse:
        """Stop the new ticker.

        Returns:
          A CountingServiceCapabilityImplementationResponse object. The success value will be:
            True - if counter was stopped successfully
            False - if counter was already not running and this was called
        """
        if not self.state.counting:
            return CountingServiceCapabilityImplementationResponse(
                state=self.state,
                success=False,
            )
        self.state.counting = False
        self.counter_thread.join()
        self.counter_thread = None
        return CountingServiceCapabilityImplementationResponse(
            state=self.state,
            success=True,
        )

    @intersect_message()
    def reset_count(self, start_again: bool) -> CountingServiceCapabilityImplementationState:
        """Set the counter back to 0.

        Params
          start_again: if True, start the counter again; if False, the
            counter will remain off.

        Returns:
          the state BEFORE the counter was reset
        """
        original_state = self.state.model_copy()
        if self.state.counting:
            self.stop_count()
        self.state.count = 0
        if start_again:
            self.start_count()
        return original_state

    def _run_count(self) -> None:
        """This is an example of a function which will NOT be exposed to INTERSECT.

        This is just the thread which increments the counter.
        """
        while self.state.counting:
            self.state.count += 1
            time.sleep(1.0)


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
    capability.capability_name = 'CountingExample'
    service = IntersectService([capability], config)
    logger.info('Starting counting_service, use Ctrl+C to exit.')
    default_intersect_lifecycle_loop(
        service,
    )

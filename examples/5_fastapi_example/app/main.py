"""Main file to start backend server.

This file shows how to implement an INTERSECT Service inside of a FastAPI server.
This is a fairly limited example which shows off a basic request/response handler from INTERSECT, and
also allows you to emit an event from an HTTP POST request.


"""

import logging
import typing
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from intersect_sdk import (
    IntersectBaseCapabilityImplementation,
    IntersectEventDefinition,
    IntersectService,
    IntersectServiceConfig,
    intersect_message,
)

from .shared import (
    CAPABILITY_NAME,
    EVENT_NAME,
    MockInputType,
    MockOutputType,
    do_mock_compute,
    get_service_hierarchy,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('fastapi_intersect_asgi_app_server')

################## INTERSECT stuff ####################


class FastAPICapability(IntersectBaseCapabilityImplementation):
    """The INTERSECT-SDK Capability.

    In addition to being added to the INTERSECT Service, this can be accessed via FastAPI via global state.
    """

    intersect_sdk_capability_name = CAPABILITY_NAME
    intersect_sdk_events: typing.ClassVar[dict[str, IntersectEventDefinition]] = {
        EVENT_NAME: IntersectEventDefinition(event_type=MockOutputType),
    }

    @intersect_message
    def intersect_request(self, param: MockInputType) -> MockOutputType:
        """Simple response generation."""
        output = do_mock_compute(param)
        output.message = 'Origin from INTERSECT'
        # returns response over INTERSECT
        return output


################## FASTAPI CORE #####################


@asynccontextmanager
async def fastapi_lifespan(app: FastAPI) -> typing.AsyncGenerator[None, None]:
    """This is the application lifecycle function that you attach to the FastAPI object, use this instead of default_intersect_lifecycle_loop.

    Startup occurs before the 'yield', cleanup after the 'yield'.
    """
    # On startup
    logger.info('Initializing app')

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

    capability = FastAPICapability()
    service = IntersectService(
        [capability],
        IntersectServiceConfig(
            hierarchy=get_service_hierarchy(),
            status_interval=30.0,
            **from_config_file,
        ),
    )
    app.state.capability = capability
    service.startup()

    logger.info('App initialized')

    yield

    # On cleanup
    logger.info('Shutting down gracefully')

    service.shutdown('Shutdown request by user')

    logger.info('Graceful shutdown complete')


app = FastAPI(
    debug=True,
    lifespan=fastapi_lifespan,
)

###################### FASTAPI ROUTES ####################################


@app.post('/')
async def publish_event(request: Request, input_value: MockInputType) -> Response:
    """The FastAPI HTTP POST endpoint, this also publishes an INTERSECT event before returning the response. The response will be received prior to the event."""
    output = do_mock_compute(input_value)
    output.message = 'Origin from FastAPI - INTERSECT'
    # send output back over INTERSECT
    request.app.state.capability.intersect_sdk_emit_event(EVENT_NAME, output)
    output.message = 'Origin from FastAPI - HTTP response'
    return output

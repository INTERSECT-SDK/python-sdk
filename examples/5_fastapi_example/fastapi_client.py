"""Client for the FastAPI example.

This Client will submit one request over INTERSECT and one request over HTTP. Both requests will receive responses in INTERSECT.
"""

import argparse
import logging
import urllib
import urllib.request

from intersect_sdk import (
    INTERSECT_RESPONSE_VALUE,
    IntersectClient,
    IntersectClientCallback,
    IntersectClientConfig,
    IntersectDirectMessageParams,
    IntersectEventMessageParams,
    default_intersect_lifecycle_loop,
)

from .app.shared import (
    CAPABILITY_NAME,
    EVENT_NAME,
    MockInputType,
    MockOutputType,
    get_service_hierarchy,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server_hierarchy = get_service_hierarchy()


class SampleOrchestrator:
    """Simple orchestrator."""

    def __init__(self) -> None:
        """Initialize a message counter to 0, for interruption later."""
        self.event_counter = 0

    def message_callback(
        self,
        _source: str,
        _operation: str,
        _has_error: bool,
        payload: INTERSECT_RESPONSE_VALUE,
    ) -> None:
        """Received from the INTERSECT message."""
        validated_response = MockOutputType(**payload)
        print(validated_response.message)
        self.event_counter += 1
        if self.event_counter >= 2:
            raise Exception('Client loop ended')  # noqa: EM101, TRY003
        # send no additional messages

    def event_callback(
        self,
        _source: str,
        _capability_name: str,
        _event_name: str,
        payload: INTERSECT_RESPONSE_VALUE,
    ) -> None:
        """Received by the INTERSECT event, this is triggered by the FastAPI request."""
        validated_response = MockOutputType(**payload)
        print(validated_response.message)
        self.event_counter += 1
        if self.event_counter >= 2:
            raise Exception('Client loop ended')  # noqa: TRY003, EM101
        # send no additional messages


def generate_mock_input() -> MockInputType:
    """Dummy request body generator."""
    return MockInputType(param_1=13.37, param_2=42069, param_3=42)


class Poster:
    """Wrapper class to be able to POST a message after startup."""

    def __init__(self, server_uri: str) -> None:
        """Server URI determined from CLI args."""
        self.server_uri = server_uri

    def publish_one_message(self) -> None:
        """Called once by internal INTERSECT logic. This is called AFTER making the HTTP request."""
        data = generate_mock_input().model_dump_json().encode()
        request = urllib.request.Request(  # noqa: S310
            self.server_uri, data, headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(request) as req:  # noqa: S310
            print(MockOutputType.model_validate_json(req.read()).message)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server-scheme', default='http')
    parser.add_argument('--server-host', default='127.0.0.1')
    parser.add_argument('--server-port', type=int, default=8000)
    args = parser.parse_args()

    server_uri = f'{args.server_scheme}://{args.server_host}:{args.server_port}'
    poster = Poster(server_uri)

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

    # Listen for an event on the exposed service
    events = [
        IntersectEventMessageParams(
            hierarchy=server_hierarchy.hierarchy_string('.'),
            capability_name=CAPABILITY_NAME,
            event_name=EVENT_NAME,
        )
    ]
    initial_messages = [
        IntersectDirectMessageParams(
            destination=server_hierarchy.hierarchy_string('.'),
            operation=f'{CAPABILITY_NAME}.intersect_request',
            payload=generate_mock_input(),
        )
    ]
    config = IntersectClientConfig(
        initial_message_event_config=IntersectClientCallback(
            services_to_start_listening_for_events=events,
            messages_to_send=initial_messages,
        ),
        **from_config_file,
    )
    orchestrator = SampleOrchestrator()
    client = IntersectClient(
        config=config,
        user_callback=orchestrator.message_callback,
        event_callback=orchestrator.event_callback,
    )

    # we should get the response from the initial request/response INTERSECT endpoint back before we get the event message or the HTTP response back
    default_intersect_lifecycle_loop(
        client,
        post_startup_callback=poster.publish_one_message,
    )

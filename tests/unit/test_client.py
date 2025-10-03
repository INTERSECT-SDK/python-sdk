from __future__ import annotations

import time
from threading import Event, Thread
from unittest.mock import MagicMock

from intersect_sdk.client import IntersectClient
from intersect_sdk.client_callback_definitions import IntersectClientCallback
from intersect_sdk.config.client import IntersectClientConfig
from intersect_sdk.shared_callback_definitions import IntersectDirectMessageParams


def test_timeout_callback_is_called():
    """Tests that the timeout callback is called when a request times out."""
    config = IntersectClientConfig(
        system='test',
        facility='test',
        organization='test',
        brokers=[
            {
                'host': 'localhost',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
                'username': 'test',
                'password': 'test',
            }
        ],
        initial_message_event_config=IntersectClientCallback(),
        terminate_after_initial_messages=True,
    )

    timeout_called = []

    def on_timeout(operation_id):
        timeout_called.append(operation_id)

    def user_callback(source, operation_id, has_error, payload):
        pass

    client = IntersectClient(config, user_callback=user_callback)

    # Mock the control plane and data plane managers
    client._control_plane_manager = MagicMock()
    client._control_plane_manager.is_connected.return_value = True
    client._control_plane_manager.considered_unrecoverable.return_value = False
    client._data_plane_manager = MagicMock()
    client._data_plane_manager.outgoing_message_data_handler.return_value = b'test'

    # Manually start the timeout thread (since startup() would try to connect)
    client._stop_timeout_thread = Event()
    client._timeout_thread = Thread(target=client._check_timeouts, daemon=True)
    client._timeout_thread.start()

    message = IntersectDirectMessageParams(
        destination='test.test.test.test.test',
        operation='test_op',
        payload='test',
        timeout=0.1,
        on_timeout=on_timeout,
    )

    client._send_userspace_message(message)

    # Wait for timeout to trigger
    time.sleep(0.3)

    assert len(timeout_called) == 1
    assert timeout_called[0] == 'test_op'

    # Clean up
    client._stop_timeout_thread.set()
    client._timeout_thread.join()


def test_timeout_callback_is_not_called():
    """Tests that the timeout callback is not called when a request is fulfilled."""
    config = IntersectClientConfig(
        system='test',
        facility='test',
        organization='test',
        brokers=[
            {
                'host': 'localhost',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
                'username': 'test',
                'password': 'test',
            }
        ],
        initial_message_event_config=IntersectClientCallback(),
        terminate_after_initial_messages=True,
    )

    timeout_called = []

    def on_timeout(operation_id):
        timeout_called.append(operation_id)

    user_callback_called = []

    def user_callback(source, operation_id, has_error, payload):
        user_callback_called.append(True)

    client = IntersectClient(config, user_callback=user_callback)

    # Mock the control plane and data plane managers
    client._control_plane_manager = MagicMock()
    client._control_plane_manager.is_connected.return_value = True
    client._control_plane_manager.considered_unrecoverable.return_value = False
    client._data_plane_manager = MagicMock()
    client._data_plane_manager.outgoing_message_data_handler.return_value = b'test'
    client._data_plane_manager.incoming_message_data_handler.return_value = b'"test"'

    # Manually start the timeout thread
    client._stop_timeout_thread = Event()
    client._timeout_thread = Thread(target=client._check_timeouts, daemon=True)
    client._timeout_thread.start()

    message = IntersectDirectMessageParams(
        destination='test.test.test.test.test',
        operation='test_op',
        payload='test',
        timeout=0.5,
        on_timeout=on_timeout,
    )

    client._send_userspace_message(message)

    # Simulate receiving a response before the timeout
    from datetime import datetime, timezone
    from uuid import uuid4

    response_message = {
        'messageId': str(uuid4()),
        'headers': {
            'source': 'test.test.test.test.test',
            'destination': client._hierarchy.hierarchy_string('.'),
            'has_error': False,
            'sdk_version': '0.8.0',
            'created_at': datetime.now(timezone.utc),
            'data_handler': 0,  # IntersectDataHandler.MESSAGE
        },
        'operationId': 'test_op',
        'payload': 'test',
        'contentType': 'application/json',
    }

    client._handle_userspace_message(response_message)

    # Wait to make sure timeout doesn't fire
    time.sleep(0.7)

    assert len(timeout_called) == 0
    assert len(user_callback_called) == 1

    # Clean up
    client._stop_timeout_thread.set()
    client._timeout_thread.join()


def test_response_after_timeout_is_ignored():
    """Tests that responses arriving after timeout are ignored and user_callback is not called."""
    config = IntersectClientConfig(
        system='test',
        facility='test',
        organization='test',
        brokers=[
            {
                'host': 'localhost',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
                'username': 'test',
                'password': 'test',
            }
        ],
        initial_message_event_config=IntersectClientCallback(),
        terminate_after_initial_messages=True,
    )

    timeout_called = []

    def on_timeout(operation_id):
        timeout_called.append(operation_id)

    user_callback_called = []

    def user_callback(source, operation_id, has_error, payload):
        user_callback_called.append(True)

    client = IntersectClient(config, user_callback=user_callback)

    # Mock the control plane and data plane managers
    client._control_plane_manager = MagicMock()
    client._control_plane_manager.is_connected.return_value = True
    client._control_plane_manager.considered_unrecoverable.return_value = False
    client._data_plane_manager = MagicMock()
    client._data_plane_manager.outgoing_message_data_handler.return_value = b'test'
    client._data_plane_manager.incoming_message_data_handler.return_value = b'"test"'

    # Manually start the timeout thread
    client._stop_timeout_thread = Event()
    client._timeout_thread = Thread(target=client._check_timeouts, daemon=True)
    client._timeout_thread.start()

    message = IntersectDirectMessageParams(
        destination='test.test.test.test.test',
        operation='test_op',
        payload='test',
        timeout=0.1,
        on_timeout=on_timeout,
    )

    client._send_userspace_message(message)

    # Wait for timeout to trigger
    time.sleep(0.3)

    # Timeout should have been called
    assert len(timeout_called) == 1
    assert timeout_called[0] == 'test_op'

    # Now simulate receiving a late response after timeout
    from datetime import datetime, timezone
    from uuid import uuid4

    response_message = {
        'messageId': str(uuid4()),
        'headers': {
            'source': 'test.test.test.test.test',
            'destination': client._hierarchy.hierarchy_string('.'),
            'has_error': False,
            'sdk_version': '0.8.0',
            'created_at': datetime.now(timezone.utc),
            'data_handler': 0,  # IntersectDataHandler.MESSAGE
        },
        'operationId': 'test_op',
        'payload': 'test',
        'contentType': 'application/json',
    }

    client._handle_userspace_message(response_message)

    # User callback should NOT have been called since the request already timed out
    assert len(user_callback_called) == 0

    # Clean up
    client._stop_timeout_thread.set()
    client._timeout_thread.join()

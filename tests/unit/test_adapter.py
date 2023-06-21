import json
import threading
import time

import pytest

from intersect import messages


@pytest.fixture
def target_capabilities(mock_adapter):
    target = dict(mock_adapter.hierarchy)
    capabilities = [
        {"name": "Availability_Status", "properties": {"status": 4, "statusDescription": ""}}
    ]
    # order defined is important
    target["capabilities"] = capabilities
    target["argument_schema"] = mock_adapter.argument_schema
    return target


def target_add_description(target, description):
    """Utility function to add status description to capabilities

    Args:
        target: The target_capabilities pytest fixture
        description: Description to add to the capabilities.properties.statusDescription
    Returns:
        The target with the new description added
    """
    target["capabilities"][0]["properties"]["statusDescription"] = description
    return target


def test_adapter(mock_adapter):
    """Test defaults for Adapter object"""
    assert mock_adapter.service_name == "foo"
    assert next(mock_adapter.identifier) == "foo0"
    assert mock_adapter.uptime == 0.0


def test_generate_action(mock_adapter):
    """Test the generate_action method"""
    action = mock_adapter._generate_action(messages.Action.START)
    assert action.header.source == "foo"
    assert action.header.destination == "None"
    assert action.header.message_id == "foo0"
    assert action.header.created
    assert action.arguments == "null"
    assert action.action == messages.Action.START

    action = mock_adapter._generate_action(messages.Action.STOP)
    assert action.action == messages.Action.STOP


def test_generate_request(mock_adapter):
    """Test the generate_request method"""
    action = mock_adapter._generate_request(messages.Request.STATUS)
    assert action.request == messages.Request.STATUS
    assert json.dumps(mock_adapter.hierarchy) == action.arguments


def test_generate_request_with_args(mock_adapter):
    """Test the generate_request method and passing arguments"""
    args = {"foo": "bar"}
    action = mock_adapter._generate_request(messages.Request.STATUS, arguments=args)
    target = json.dumps({**mock_adapter.hierarchy, **args})
    assert target == action.arguments


def test_status_ticker(monkeypatch, mock_adapter):
    """Test starting and stopping the status ticker"""
    # Make the status ticker exit quickly
    interval_in_seconds = 1.0
    mock_adapter.status_ticker_interval = interval_in_seconds
    assert mock_adapter.status_ticker_interval == interval_in_seconds

    # Check status ticker is active and start status messages
    assert mock_adapter.status_ticker_active is True
    start_status_ticker_thread = threading.Thread(target=mock_adapter.start_status_ticker)
    start_status_ticker_thread.start()

    # Stop status messages and check ticker is no longer active
    stop_status_ticker_thread = threading.Thread(target=mock_adapter.stop_status_ticker)
    stop_status_ticker_thread.start()
    assert mock_adapter.status_ticker_active is False
    time.sleep(0.5)  # so status ticker thread is not stopped before it starts

    start_status_ticker_thread.join()
    stop_status_ticker_thread.join()


def test_create_status(mock_adapter):
    """Test the private create status method"""
    msg = mock_adapter._create_status()
    assert msg.status == messages.Status.GENERAL
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    assert msg.detail == json.dumps(mock_adapter.hierarchy)


def test_generate_status_online(mock_adapter, target_capabilities):
    """Test the generate status method for ONLINE message type"""
    msg = mock_adapter.generate_status_online()
    assert msg.status == messages.Status.ONLINE
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    target = target_add_description(
        target_capabilities,
        description=f"Service {msg.header.source} is online.",
    )
    assert msg.detail == json.dumps(target)


def test_generate_status_offline(mock_adapter, target_capabilities):
    """Test the generate status method for OFFLINE message type"""
    msg = mock_adapter.generate_status_offline()
    assert msg.status == messages.Status.OFFLINE
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    target = target_add_description(
        target_capabilities,
        description=f"Service {msg.header.source} is offline.",
    )
    assert msg.detail == json.dumps(target)


def test_generate_status_starting(mock_adapter, target_capabilities):
    """Test the generate status method for STARTING message type"""
    msg = mock_adapter.generate_status_starting()
    assert msg.status == messages.Status.STARTING
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    target = target_add_description(
        target_capabilities,
        description=f"Service {msg.header.source} online, starting normal status ticker.",
    )
    assert msg.detail == json.dumps(target)


def test_generate_status_stopping(mock_adapter, target_capabilities):
    """Test the generate status method for STOPPING message type"""
    msg = mock_adapter.generate_status_stopping()
    assert msg.status == messages.Status.STOPPING
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"

    target = target_add_description(
        target_capabilities,
        description=f"Service {msg.header.source} is stopping.",
    )
    assert msg.detail == json.dumps(target)


def test_generate_status_available(mock_adapter):
    """Test the generate status method for AVAILABLE message type"""
    msg = mock_adapter.generate_status_available()
    assert msg.status == messages.Status.AVAILABLE
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    assert msg.detail == json.dumps(mock_adapter.hierarchy)


def test_generate_status_ready(mock_adapter):
    """Test the generate status method for READY message type"""
    msg = mock_adapter.generate_status_ready()
    assert msg.status == messages.Status.READY
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    assert msg.detail == json.dumps(mock_adapter.hierarchy)


def test_generate_status_busy(mock_adapter):
    """Test the generate status method for BUSY message type"""
    msg = mock_adapter.generate_status_busy()
    assert msg.status == messages.Status.BUSY
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    assert msg.detail == json.dumps(mock_adapter.hierarchy)


def test_generate_status_general(mock_adapter):
    """Test the generate status method for GENERAL message type"""
    msg = mock_adapter.generate_status_general()
    assert msg.status == messages.Status.GENERAL
    assert msg.header.source == "foo"
    assert msg.header.destination == "None"
    assert msg.header.message_id == "foo0"
    assert msg.detail == json.dumps(mock_adapter.hierarchy)

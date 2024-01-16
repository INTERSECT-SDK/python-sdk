import json
from typing import Callable
from unittest.mock import Mock

import pytest
from intersect_sdk import messages
from intersect_sdk.client.channel import Channel

mock_broker = Mock()


def test_channel_serializer_status() -> None:
    channel = Channel('test', mock_broker)

    message = messages.Status()
    serialized_message = channel.serializer.serialize(message)
    serialized_message_json = json.loads(serialized_message)
    assert serialized_message_json.get('type') == 'STATUS'
    assert serialized_message_json.get('length') == 2
    assert serialized_message_json.get('message') == '{}'


def test_channel_serializer_request() -> None:
    channel = Channel('test', mock_broker)

    message = messages.Request()
    serialized_message = channel.serializer.serialize(message)
    serialized_message_json = json.loads(serialized_message)
    assert serialized_message_json.get('type') == 'REQUEST'
    assert serialized_message_json.get('length') == 2
    assert serialized_message_json.get('message') == '{}'


@pytest.mark.skip("not working: Action doesn't contain a type???")
def test_channel_serializer_action() -> None:
    channel = Channel('test', mock_broker)

    message = messages.Action()
    serialized_message = channel.serializer.serialize(message)
    serialized_message_json = json.loads(serialized_message)
    assert serialized_message_json.get('type') == 'ACTION'
    assert serialized_message_json.get('length') == 2
    assert serialized_message_json.get('message') == '{}'


def test_channel_publish() -> None:
    channel = Channel('test', mock_broker)
    message = messages.Status()

    channel.publish(message)

    mock_broker.publish.assert_called()
    mock_broker.reset_mock()


def test_channel_subscribe() -> None:
    channel = Channel('test', mock_broker)

    channel.subscribe(None)
    assert isinstance(channel.handler.serializer, messages.JsonHandler)
    assert channel.handler.callback is None

    mock_broker.subscribe.assert_called()
    mock_broker.reset_mock()


def test_channel_callback() -> None:
    # Details in the message that will become the payload in the callback
    detail = 'details in the  message'

    def callback(payload: str) -> None:
        assert payload.detail == detail

    channel = Channel('test', mock_broker)
    handler = channel.ChannelCallback(callback)
    assert isinstance(handler.serializer, messages.JsonHandler)
    assert isinstance(handler.callback, Callable)

    # Create message and serialize so we can deserialize in the callback
    message = messages.Status(detail=detail)
    serialized_message = channel.serializer.serialize(message)
    handler.on_receive('topic', serialized_message)

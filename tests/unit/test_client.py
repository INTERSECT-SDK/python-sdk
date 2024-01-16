from unittest.mock import Mock

import httpretty
from intersect_sdk.brokers import amqp_client, broker_client, mqtt_client
from intersect_sdk.client import Client
from intersect_sdk.client.channel import Channel
from intersect_sdk.messages import BinaryHandler, JsonHandler
from intersect_sdk.messages.handlers.serialization_handler import SerializationHandler

mock_broker = Mock()


def mock_function_amqp(backend_name):
    assert backend_name == 'rabbitmq-amqp'
    return mock_broker


def mock_function_mqtt(backend_name):
    assert backend_name == 'rabbitmq-mqtt'
    return mock_broker


def test_create_broker() -> None:
    client = Client('test_clien_test_create_broker')
    broker = client._create_broker_client('rabbitmq-mqtt')
    assert isinstance(broker, mqtt_client.MQTTClient)

    broker = client._create_broker_client('rabbitmq-amqp')
    assert isinstance(broker, amqp_client.AMQPClient)


def test_connect_calls_broker() -> None:
    client = Client('test_clien_test_connect_calls_broker')
    client._create_broker_client = mock_function_mqtt
    client.connect(('', ''), '', '')

    mock_broker.connect.assert_called()
    mock_broker.reset_mock()


@httpretty.activate
def test_connect_calls_discovery_service() -> None:
    httpretty.register_uri(
        httpretty.GET,
        'http://discovery_address/v0.1/intersect-broker',
        body=r'{"backendName":"rabbitmq-amqp","endpoint":"ip:port"}',
    )

    client = Client('test_clien_test_connect_calls_discovery_service')
    client._create_broker_client = mock_function_amqp

    client.connect(('http://discovery_address', '', True), 'username', 'passwd')

    mock_broker.connect.assert_called_with('ip', 'port', 'username', 'passwd')
    mock_broker.reset_mock()


@httpretty.activate
def test_connect_can_use_another_endpoint() -> None:
    httpretty.register_uri(
        httpretty.GET,
        'http://discovery_address/v0.1/intersect-broker-mqtt',
        body=r'{"backendName":"rabbitmq-mqtt","endpoint":"ip:port"}',
    )

    client = Client('test_clien_test_connect_can_use_another_endpoint')
    client._broker_endpoint = 'intersect-broker-mqtt'
    client._create_broker_client = mock_function_mqtt

    client.connect(
        ('http://discovery_address', '', True, 'intersect-broker-mqtt'), 'username', 'passwd'
    )

    mock_broker.connect.assert_called_with('ip', 'port', 'username', 'passwd')
    mock_broker.reset_mock()


def test_amqp_client_creates_channel() -> None:
    client = Client('test_clien_test_amqp_client_creates_channel')
    client.broker_client = client._create_broker_client('rabbitmq-amqp')

    channel = client.channel('amqp-broker-json-handler-channel')
    assert isinstance(channel, Channel)
    assert isinstance(channel.broker, broker_client.BrokerClient)
    assert isinstance(channel.broker, amqp_client.AMQPClient)
    assert isinstance(channel.serializer, SerializationHandler)
    assert isinstance(channel.serializer, JsonHandler)

    channel = client.channel('amqp-broker-binary-handler-channel', serializer=BinaryHandler())
    assert isinstance(channel, Channel)
    assert isinstance(channel.broker, broker_client.BrokerClient)
    assert isinstance(channel.broker, amqp_client.AMQPClient)
    assert isinstance(channel.serializer, SerializationHandler)
    assert isinstance(channel.serializer, BinaryHandler)


def test_mqtt_client_creates_channel() -> None:
    client = Client('test_clien_test_mqtt_client_creates_channel')
    client.broker_client = client._create_broker_client('rabbitmq-mqtt')

    channel = client.channel('mqtt-broker-json-handler-channel')
    assert isinstance(channel, Channel)
    assert isinstance(channel.broker, broker_client.BrokerClient)
    assert isinstance(channel.broker, mqtt_client.MQTTClient)
    assert isinstance(channel.serializer, SerializationHandler)
    assert isinstance(channel.serializer, JsonHandler)

    channel = client.channel('mqtt-broker-binary-handler-channel', serializer=BinaryHandler())
    assert isinstance(channel, Channel)
    assert isinstance(channel.broker, broker_client.BrokerClient)
    assert isinstance(channel.broker, mqtt_client.MQTTClient)
    assert isinstance(channel.serializer, SerializationHandler)
    assert isinstance(channel.serializer, BinaryHandler)

# standard
import os
import unittest
from time import sleep

# project
from intersect_sdk.brokers import mqtt_client

# local
from tests.fixtures.example_message_handler import ExampleMessageHandler


class TestMqttClient(unittest.TestCase):
    """
    Unit tests for the mqtt_client class.
    """

    def test_connect(self):
        """
        Test that the client can create a connection to the server.
        """

        # Open the connection
        client = mqtt_client.MQTTClient("test_mqtt_broker_client_test_connect")
        client.connect(
            os.environ["RABBITMQ_HOST"],
            1883,
            os.environ["RABBITMQ_USERNAME"],
            os.environ["RABBITMQ_PASSWORD"],
        )

        # Check that the connection exists
        self.assertTrue(client._connection)

    def test_subscribe(self):
        """
        Test that the client can publish messages and subscribe to topics
        """

        # The connection should start closed
        client = mqtt_client.MQTTClient("test_mqtt_broker_client_test_subscribe")
        self.assertFalse(client.is_connected())

        # Open a connection
        client.connect(
            os.environ["RABBITMQ_HOST"],
            1883,
            os.environ["RABBITMQ_USERNAME"],
            os.environ["RABBITMQ_PASSWORD"],
        )

        # Handler that will pass messages along
        normalHandler1 = ExampleMessageHandler(True)

        # Secondary handler after normalHandler1 that should get messages that
        # are passed to it
        normalHandler2 = ExampleMessageHandler(False)

        # Secondary handler after normalHandler1 that will block further
        # handlers from receiving messages
        blockHandler = ExampleMessageHandler(False)

        # Handler that won't receive anything because it is the third handler
        # in the chain after block handler
        emptyHandler = ExampleMessageHandler(True)

        # Subscribe handlers such that the queues are:
        #  -topic 1 (normalHandler1 -> normalHandler2)
        #  -topic 2 (normalHandler1 -> blockHandler -> emptyHandler)
        client.subscribe(["mqtt_client_topic1", "mqtt_client_topic2"], normalHandler1)
        client.subscribe(["mqtt_client_topic1"], normalHandler2)
        client.subscribe(["mqtt_client_topic2"], blockHandler)
        client.subscribe(["mqtt_client_topic2"], emptyHandler)

        # Publish data 1 and 2 on topic1, dat 3 and 4 on topic 2, and data 5
        # on a topic nothing is subscribed to
        client.publish("mqtt_client_topic1", "data1")
        client.publish("mqtt_client_topic1", "data2")
        client.publish("mqtt_client_topic2", "data3")
        client.publish("mqtt_client_topic2", "data4")
        client.publish("mqtt_client_wrong_topic", "data5")

        # Give the RabbitMQ client some time to get the messages
        sleep(5)

        # The client will be connected after subscribing
        self.assertTrue(client.is_connected())

        # The normal handler should have gotten all data on the correct channels
        mqtt_client_topic1Normal1 = normalHandler1.get_messages("mqtt_client_topic1")
        self.assertEqual(2, len(mqtt_client_topic1Normal1))
        self.assertTrue(b"data1" in mqtt_client_topic1Normal1)
        self.assertTrue(b"data2" in mqtt_client_topic1Normal1)
        mqtt_client_topic2Normal1 = normalHandler1.get_messages("mqtt_client_topic2")
        self.assertEqual(2, len(mqtt_client_topic2Normal1))
        self.assertTrue(b"data3" in mqtt_client_topic2Normal1)
        self.assertTrue(b"data4" in mqtt_client_topic2Normal1)

        # Normal handler 2 should have gotten the data for topic1
        mqtt_client_topic1Normal2 = normalHandler2.get_messages("mqtt_client_topic1")
        self.assertEqual(2, len(mqtt_client_topic1Normal2))
        self.assertTrue(b"data1" in mqtt_client_topic1Normal2)
        self.assertTrue(b"data2" in mqtt_client_topic1Normal2)

        # Normal handler 2 was not subscribed to topic 2
        self.assertEqual(0, len(normalHandler2.get_messages("mqtt_client_topic2")))

        # Block and empty handler were not subsribed to topic 1
        self.assertEqual(0, len(blockHandler.get_messages("mqtt_client_topic1")))
        self.assertEqual(0, len(emptyHandler.get_messages("mqtt_client_topic1")))

        # Nobody should have gotten anything over wrong_topic
        self.assertEqual(0, len(normalHandler1.get_messages("mqtt_client_wrong_topic")))
        self.assertEqual(0, len(normalHandler2.get_messages("mqtt_client_wrong_topic")))
        self.assertEqual(0, len(blockHandler.get_messages("mqtt_client_wrong_topic")))
        self.assertEqual(0, len(emptyHandler.get_messages("mqtt_client_wrong_topic")))

        # The block handler should have gotten the data on topic 2
        mqtt_client_topic2Block = blockHandler.get_messages("mqtt_client_topic2")
        self.assertEqual(2, len(mqtt_client_topic2Block))
        self.assertTrue(b"data3" in mqtt_client_topic2Block)
        self.assertTrue(b"data4" in mqtt_client_topic2Block)

        # The empty handler should not have gotten the data on topic 2 despite
        # the subscription because it was blocked by the block handler
        self.assertEqual(0, len(emptyHandler.get_messages("mqtt_client_topic2")))

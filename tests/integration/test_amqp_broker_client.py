# standard
import os
import unittest
from time import sleep

# project
from intersect.brokers import amqp_client

# local
from tests.fixtures.example_message_handler import ExampleMessageHandler


class TestAmqpClient(unittest.TestCase):
    """
    Unit tests for the amqp_client class.
    """

    def test_connect(self):
        """
        Test that the client can create a connection to the server.
        """

        # Open the connection

        client = amqp_client.AMQPClient()

        client.connect(
            os.environ["RABBITMQ_HOST"],
            5672,
            os.environ["RABBITMQ_USERNAME"],
            os.environ["RABBITMQ_PASSWORD"],
        )

        # Check that the connection exists
        self.assertTrue(client._connection_params)

        # Check that the connection is active
        self.assertTrue(client.is_connected())

        client.close_connections()

        # Check that the connection closed
        self.assertFalse(client.is_connected())

    def test_subscribe_2clients(self):
        client1 = amqp_client.AMQPClient(uid="123")
        client2 = amqp_client.AMQPClient()
        client1.connect(
            os.environ["RABBITMQ_HOST"],
            5672,
            os.environ["RABBITMQ_USERNAME"],
            os.environ["RABBITMQ_PASSWORD"],
        )
        client2.connect(
            os.environ["RABBITMQ_HOST"],
            5672,
            os.environ["RABBITMQ_USERNAME"],
            os.environ["RABBITMQ_PASSWORD"],
        )
        normalHandler1 = ExampleMessageHandler(True)
        normalHandler2 = ExampleMessageHandler(True)
        client1.subscribe(["amqp_client_topic1"], normalHandler1)
        client2.subscribe(["amqp_client_topic1"], normalHandler2)

        # any client can publish, id does not matter
        client1.publish("amqp_client_topic1", "data1")
        client2.publish("amqp_client_topic1", "data2")
        sleep(5)
        client1.close_connections()
        client2.close_connections()

        amqp_client_topic1Normal1 = normalHandler1.get_messages("amqp_client_topic1")
        amqp_client_topic1Normal2 = normalHandler2.get_messages("amqp_client_topic1")
        self.assertEqual(2, len(amqp_client_topic1Normal1), "client1")
        self.assertEqual(2, len(amqp_client_topic1Normal2), "client2")

    def test_subscribe(self):
        """
        Test that the client can publish messages and subscribe to topics
        """

        # Open a connection
        client = amqp_client.AMQPClient(uid="123")
        client.connect(
            os.environ["RABBITMQ_HOST"],
            5672,
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

        client.subscribe(["amqp_client_topic1", "amqp_client_topic2"], normalHandler1)
        client.subscribe(["amqp_client_topic1"], normalHandler2)
        client.subscribe(["amqp_client_topic2"], blockHandler)
        client.subscribe(["amqp_client_topic2"], emptyHandler)

        # Publish data 1 and 2 on topic1, dat 3 and 4 on topic 2, and data 5
        # on a topic nothing is subscribed to
        client.publish("amqp_client_topic1", "data1")
        client.publish("amqp_client_topic1", "data2")
        client.publish("amqp_client_topic2", "data3")
        client.publish("amqp_client_topic2", "data4")
        client.publish("amqp_client_wrong_topic", "data5")

        # Give the RabbitMQ client some time to get the messages
        sleep(5)
        client.close_connections()

        # The normal handler should have gotten all data on the correct channels
        amqp_client_topic1Normal1 = normalHandler1.get_messages("amqp_client_topic1")
        self.assertEqual(2, len(amqp_client_topic1Normal1))
        self.assertTrue(b"data1" in amqp_client_topic1Normal1)
        self.assertTrue(b"data2" in amqp_client_topic1Normal1)
        amqp_client_topic2Normal1 = normalHandler1.get_messages("amqp_client_topic2")
        self.assertEqual(2, len(amqp_client_topic2Normal1))
        self.assertTrue(b"data3" in amqp_client_topic2Normal1)
        self.assertTrue(b"data4" in amqp_client_topic2Normal1)

        # Normal handler 2 should have gotten the data for topic1
        amqp_client_topic1Normal2 = normalHandler2.get_messages("amqp_client_topic1")
        self.assertEqual(2, len(amqp_client_topic1Normal2))
        self.assertTrue(b"data1" in amqp_client_topic1Normal2)
        self.assertTrue(b"data2" in amqp_client_topic1Normal2)

        # Normal handler 2 was not subscribed to topic 2
        self.assertEqual(0, len(normalHandler2.get_messages("amqp_client_topic2")))

        # Block and empty handler were not subsribed to topic 1
        self.assertEqual(0, len(blockHandler.get_messages("amqp_client_topic1")))
        self.assertEqual(0, len(emptyHandler.get_messages("amqp_client_topic1")))

        # Nobody should have gotten anything over wrong_topic
        self.assertEqual(0, len(normalHandler1.get_messages("amqp_client_wrong_topic")))
        self.assertEqual(0, len(normalHandler2.get_messages("amqp_client_wrong_topic")))
        self.assertEqual(0, len(blockHandler.get_messages("amqp_client_wrong_topic")))
        self.assertEqual(0, len(emptyHandler.get_messages("amqp_client_wrong_topic")))

        # The block handler should have gotten the data on topic 2
        amqp_client_topic2Block = blockHandler.get_messages("amqp_client_topic2")
        self.assertEqual(2, len(amqp_client_topic2Block))
        self.assertTrue(b"data3" in amqp_client_topic2Block)
        self.assertTrue(b"data4" in amqp_client_topic2Block)

        # The empty handler should not have gotten the data on topic 2 despite
        # the subscription because it was blocked by the block handler
        self.assertEqual(0, len(emptyHandler.get_messages("amqp_client_topic2")))

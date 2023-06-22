# project
from intersect.brokers import MessageHandler


class ExampleMessageHandler(MessageHandler):
    """
    A MessageHandler example that stores the messages it receives and allows
    the programmer to define whether future handlers will also get the messages
    """

    def __init__(self, allow):
        """
        Default constructor

        @param allow: Boolean flag for whether to allow consume messages to
                      continue along the handler chain
        """

        self.allow = allow

        self.received = {}

    def get_messages(self, topic):
        """
        Return the messages received for the given topic

        @param topic: The topic name to retrieve messages for
        @return A list of every message consumed for the given topic in the
                order it was received
        """

        if topic in self.received:
            return self.received[topic]
        else:
            return []

    def on_receive(self, topic, payload):
        """
        Handle a new message

        @param topic: The topic the message came from
        @param payload: The message contents
        @return True if subsequent handlers in the queue should also receive
                this message. False if they should not.
        """

        # If there is no list ofr this topic, make a new one
        if topic not in self.received:
            self.received[topic] = []

        # Add the new message to the end of the list
        self.received[topic].append(payload)
        return self.allow

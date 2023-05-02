# Standard imports
import logging
import os
import time

from typing import Tuple

# intersect imports
from intersect.common import adapter, common
from intersect import messages

logger = logging.getLogger(f"demo2.intersect.epics.{__file__}")
env_get = os.environ.get


class Client(adapter.Adapter):
    """ A sample Hello World client for demonstrating communication with INTERSECT messages.

    The client regularly sends Status messages containing its state. It can also send START/STOP Action messages or
    DETAIL Request messages to the example-server. DETAIL messages will prompt the reply of a GENERAL Status message,
    whose contents will be printed to the console.
    """
    # Member variables
    arguments_parser: str = "json"
    status_ticker_interval: float = float(env_get('STATUS_INTERVAL', '30.0'))
    id_counter_init: int = int(env_get('ID_COUNTER_INIT', '100'))
    handled_status: Tuple = (
        messages.Status.GENERAL,
    )

    def __init__(self,
                 system_name: str,
                 broker_address: str,
                 broker_port: int,
                 username: str,
                 password: str):
        super().__init__(system_name,
                         broker_address,
                         broker_port,
                         username,
                         password)
        self.register_message_handler(
            self.handle_status_general,
            {messages.Status: [messages.Status.GENERAL]}
        )

        # Generate and publish start message
        self.status_channel.publish(self.generate_start_status())

        # Start status ticker and start action subscribe
        self.start_status_ticker()

    @staticmethod
    def handle_status_general(message, type_, subtype, payload):
        logger.info("Count received from server: %s", payload['count'])
        return True

    def generate_start(self, destination):
        """Send a START Action message with appropriate metadata

        Args:
            destination: A string containing the service name to send the Action to.
        """
        tmp = self.generate_action_start(destination, dict())
        # The controllers might be expecting args, so send a blank dictionary

        logger.info("\033[1mSending --> STOP\n\033[0m%s", tmp)
        self.send(tmp)

    def generate_stop(self, destination):
        """Send a STOP Action message with appropriate metadata

        Args:
            destination: A string containing the service name to send the Action to.
        """
        tmp = self.generate_action_stop(destination, dict())
        # The controllers might be expecting args, so send a blank dictionary

        logger.info("\033[1mSending --> STOP\n\033[0m%s", tmp)
        self.send(tmp)

    def generate_request(self, destination):
        """Send a DETAIL Request message with appropriate metadata

        Args:
            destination: A string containing the service name to send the Request to.
        """
        tmp = self.generate_request_detail(destination, dict())
        # The controllers might be expecting args, so send a blank dictionary

        logger.info("\033[1mSending --> DETAIL\n\033[0m%s", tmp)
        self.connection.channel(destination + "/request").publish(tmp)


if __name__ == "__main__":

    # -- Arguments and logging --

    parser = common.setup_parser(system_name="example-hello_client")
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=int(os.environ.get("PUBLISH_INTERVAL_SECONDS", 5)),
        help="Interval between published messages",
    )
    parser.add_argument(
        "--example-server",
        "-e",
        type=str,
        default=str(os.environ.get("SERVER_NAME", "example-server")),
        help="Name of the example server service",
    )
    args = parser.parse_args()
    common.setup_logging(args)

    # -- Demo --

    demo = Client(
        args.system_name,
        args.broker_address,
        args.broker_port,
        args.broker_username,
        args.broker_password
    )

    # Run until the process is killed externally
    print("Press Ctrl-C to exit:")

    try:
        # Constantly request the current count, stop the count, request the count, start the count,
        # and request the count, in that order to demonstrate how the server can be controlled.
        while True:
            time.sleep(1.0)
            print(f"Uptime: {demo.uptime}", end='\r')
            demo.generate_request(args.example_server)
            demo.generate_stop(args.example_server)
            time.sleep(5.0)
            demo.generate_request(args.example_server)
            demo.generate_start(args.example_server)
            time.sleep(5.0)
            demo.generate_request(args.example_server)
            # logger.info("Uptime: %ds", demo.uptime)

    except KeyboardInterrupt:
        print("User requested exit")

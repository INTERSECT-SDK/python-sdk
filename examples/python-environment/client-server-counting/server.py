# Standard imports
import logging
import threading
import time

from typing import Tuple, Union

# intersect imports
from intersect import messages
from intersect import common

logger = logging.getLogger(common.LOGGER_INTERSECT_SDK)


class CountingAdapter(common.Adapter):
    """ An example adapter using INTERSECT

    A Adapter that can be set to send uptime status messages and to maintain a startable/stoppable count up from 0.

    Accepts the following messages:

    Action START: Starts counting up if not already doing so.

    Action RESTART: Same as START action.

    Action STOP: Stops counting up.

    Request DETAIL: Returns the current count as a Status GENERAL message to the requesting service.
    """

    # other stuff
    handled_actions: Tuple = (
        messages.Action.START,
        messages.Action.STOP,
        messages.Action.RESTART,
    )
    handled_request: Tuple = (
        messages.Request.STATUS,
        messages.Request.DETAIL,
    )

    def __init__(self,
                 system_name: str,
                 broker_address: str,
                 broker_port: int,
                 username: str,
                 password: str):

        # Setup base class
        super().__init__(system_name, broker_address, broker_port, username, password)

        # Set attributes for counting
        self.counter_thread: Union[None, threading.Thread] = None
        self.count_active: bool = True

        # Register message handlers
        self.register_message_handler(
            self.handle_start,
            {messages.Action: [messages.Action.START, messages.Action.RESTART]}
        )
        self.register_message_handler(
            self.handle_stop,
            {messages.Action: [messages.Action.STOP]}
        )
        self.register_message_handler(
            self.handle_request_detail,
            {messages.Request: [messages.Request.DETAIL]}
        )

        # Generate and publish start message
        self.status_channel.publish(self.generate_start_status())

        # Start status ticker and start action subscribe
        self.start_status_ticker()

        # Initialize the count to 0
        self.count = 0

    def _run_count(self):
        '''In a loop, while the count_active flag is set, increment the count by 1 every second.
        '''
        while self.count_active:
            self.count += 1
            time.sleep(1.0)

    def start_count(self):
        ''' Starts the counting thread

        If the counting thread does not exist, starts it. Otherwise prints a message.
        '''
        if self.counter_thread is None:
            self.counter_thread = threading.Thread(
                target=self._run_count,
                daemon=True,
                name=f"{self.system_name}_counter_thread"
            )
            self.counter_thread.start()
            logger.info("Started counting thread")
        if self.counter_thread is not None:
            logger.info("Counter thread already active")

    def stop_count(self):
        ''' Stops the counter thread.
        '''

        if self.counter_thread is not None:
            self.count_active = False
            self.counter_thread.join()
            self.counter_thread = None
            self.count_active = True
        logger.info("Stopped count")

    def restart_count(self):
        ''' Stops the counter thread if it exists, then starts a new one.
        '''

        if self.counter_thread is not None:
            self.stop_count()
        self.start_count()

    # -- Handlers --
    def handle_request_detail(self, msg, msg_type, msg_subtype, payload):
        """ Handles a DETAIL Request message.

        Creates a GENERAL Status message addressed to the sender of the Request, containing the current count.

        Args:
            message: A Request message from another system, asking for the count.
        Returns:
            True if the message was handled correctly.
        """
        reply = self.generate_status_general(detail={"count": self.count})
        reply.header.destination = msg.header.source
        self.send(reply)
        return True

    @common.adapter.status_tracker(messages.Status.READY)
    def handle_start(self, msg, msg_type, msg_subtype, payload):
        """ Start the counting in response to a START Action

        Args:
            msg: The Action message being handled.
        Returns:
            True if the message was handled correctly.
        """
        logger.info("\033[1mReceived <-- START\n\033[0m%s", msg)
        self.restart_count()
        return True

    @common.adapter.status_tracker(messages.Status.AVAILABLE)
    def handle_stop(self, msg, msg_type, msg_subtype, payload):
        """ Stop the counting in response to a STOP Action

        Args:
            msg: The Action message being handled.
        Returns:
            True if the message was handled correctly.
        """
        logger.info("\033[1mReceived <-- STOP\n\033[0m%s", msg)
        self.stop_count()
        return True


if __name__ == "__main__":

    # -- Arguments and logging --

    parser = common.setup_parser(system_name="example-server")
    args = parser.parse_args()
    common.setup_logging(args)

    # -- Demo --
    counting_adapter = CountingAdapter(
        args.system_name,
        args.broker_address,
        args.broker_port,
        args.broker_username,
        args.broker_password
    )

    # Start the adapter counting
    counting_adapter.start_count()

    # Run until the process is killed externally
    print("Press Ctrl-C to exit:")
    try:
        while True:
            # Print the uptime every second.
            time.sleep(5.0)
            print(f"Uptime: {counting_adapter.uptime}", end='\r')
    except KeyboardInterrupt:
        print("User requested exit")

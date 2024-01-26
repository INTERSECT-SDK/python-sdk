import os
import signal
import sys
from typing import NoReturn

from .logger import logger


def die(message: str, exit_code: int = 1) -> NoReturn:
    """Terminate the program.

    This should generally happen ONLY during configuration (i.e. validating Intersect configurations,
     validating schemas, validating backing service connections, etc.), but the application should eagerly terminate at this point.

    When handling callbacks from message brokers, however, the application should NOT terminate in this way.
    """
    logger.critical(message)
    # XXX - potentially consider raising a RuntimeError here - though we would prefer that RuntimeError not be catchable
    sys.exit(exit_code)


def send_os_signal(ossignal: signal.Signals = signal.SIGTERM) -> None:
    """Send a signal to break out of a loop listening for signals, and allow for code written after this loop to execute.

    NOTE: the `ossignal` param defaults to SIGTERM, which should generally be fine.
    This isn't the most "idiomatic" usage of the signal (that would be SIGUSR1, SIGUSR2, or SIGALRM)
    but that's OK.

    If you want to send a different signal, however, it MUST be portable across all major operating systems.
    This generally limits you to SIGTERM, SIGABRT, and SIGINT.
    """
    os.kill(os.getpid(), ossignal)

"""
This module defines some generic lifecycle utilities users can implement for themselves.

It IS essential for an application to be able to shut down gracefully, as the adapter can communicate
to the broader INTERSECT ecosystem that they have shut down. Obviously, not all shutdowns can be detected.

However - classes and functions in this module are not essential towards an adapter functioning properly.
If you're using something with its own lifecycle, you can safely ignore this module and implement
the calls to the adapter lifecycle functions yourself.

For example, it's possible to integrate an INTERSECT adapter with a FastAPI web server. Since FastAPI
already manages its own lifecycles, you should integrate your adapter with FastAPI manually,
and let FastAPI handle lifecycles.
"""

import signal
import sys
from threading import Event
from typing import Any, Callable, Optional, Union

from ._internal.logger import logger
from .client import IntersectClient
from .service import IntersectService


class SignalHandler:
    """
    Listen for signals sent to process and try to clean up gracefully.

    Once the constructor has been initialized, signals will be caught.


    Currently, we do not ignore any signals we catch, though debatably
    SIGHUP (terminal died), SIGQUIT (core dump), SIGUSR1, and SIGUSR2
    should be ignored.
    """

    def __init__(self, cleanup_callback: Optional[Callable[[int], None]] = None) -> None:
        """
        Parameters
        ----------

        cleanup_callback: This is an optional callback function which will be
        called once a signal is caught. The callback function takes in a single
        integer parameter, which will be the signal code intercepted.

        """
        self._exit = Event()
        self._cleanup_callback = cleanup_callback
        catchSignals = [
            signal.SIGINT,
            signal.SIGTERM,
        ]
        if sys.platform != 'win32':
            catchSignals += [
                signal.SIGHUP,
                signal.SIGQUIT,
                signal.SIGUSR1,
                signal.SIGUSR2,
            ]
        for signum in catchSignals:
            signal.signal(signum, self._on_signal_caught)

    def _on_signal_caught(self, signal: int, _: Any) -> None:
        """
        Executes when signal is caught

        Don't use this externally, but you can extend this class
        and override this method (be sure to call superclass function)
        if you'd prefer to run cleanup in this class.

        Parameters
        ----------
        signal (int): signal code.
        """
        logger.warning('shutting down and handling signal %d' % signal)
        if self._cleanup_callback:
            self._cleanup_callback(signal)
        self._exit.set()

    def should_stop(self) -> bool:
        """
        Returns
        -------
        True if signal has not been detected, False otherwise
        """
        return self._exit.is_set()

    def wait(self, amount: float) -> None:
        self._exit.wait(amount)


def default_intersect_lifecycle_loop(
    intersect_gateway: Union[IntersectClient, IntersectService],
    delay: float = 30.0,
    cleanup_callback: Optional[Callable[[int], None]] = None,
    waiting_callback: Optional[Callable[[IntersectService], None]] = None,
) -> None:
    """
    If users don't have their own lifecycle manager, they can import this one to begin a lifecycle loop. This loop
    automatically catches appropriate OS signals and allows for graceful shutdown.

    IMPORTANT: If you are integrating an INTERSECT adapter into your existing application, you should use your
    own application's lifecycle manager instead.

    Params:
      intersect_gateway: This can be either an IntersectClient or an IntersectService.
      delay (float): how often the loop should wait for (default: 30 seconds)
      cleanup_callback: This is an optional callback function which will be
        called once a signal is caught. The callback function takes in a single
        integer parameter, which will be the signal code intercepted. The function
        will be executed just before the loop ends.
      waiting_callback: This is an optional callback function which will be
        called every <DELAY> seconds. It takes in the adapter, and returns nothing.
        This can be useful to set for debugging purposes.

    """
    sighandler = SignalHandler(cleanup_callback=cleanup_callback)
    intersect_gateway.startup()
    logger.debug('INTERSECT: starting default loop')
    while not sighandler.should_stop():
        sighandler.wait(delay)
        if waiting_callback:
            waiting_callback(intersect_gateway)
    intersect_gateway.shutdown(reason='Application gracefully terminated.')

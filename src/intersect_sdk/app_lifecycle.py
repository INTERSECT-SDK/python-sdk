"""This module defines some generic lifecycle utilities users can implement for themselves. Both Clients and Services can use these utilities, but they should be considered optional.

It IS essential for an application to be able to shut down gracefully, as the adapter can communicate
to the broader INTERSECT ecosystem that they have shut down. Obviously, not all shutdowns can be detected.

However - classes and functions in this module are not essential towards an adapter functioning properly.
If you're using something with its own lifecycle, you can safely ignore this module and implement
the calls to the adapter lifecycle functions yourself.

For example, it's possible to integrate an INTERSECT adapter with a FastAPI web server. Since FastAPI
already manages its own lifecycles, you should integrate your adapter with FastAPI manually,
and let FastAPI handle lifecycles.
"""

from __future__ import annotations

import signal
import sys
from threading import Event
from typing import TYPE_CHECKING, Any, Callable

from ._internal.logger import logger
from ._internal.utils import die

if TYPE_CHECKING:
    from .client import IntersectClient
    from .service import IntersectService


class SignalHandler:
    """Listen for signals sent to process and try to clean up gracefully.

    Once the constructor has been initialized, signals will be caught.

    We catch the following signals, based on platform support:
      - SIGINT (same as Ctrl+C)
      - SIGTERM
      - SIGHUP
      - SIGQUIT
      - SIGUSR1
      - SIGUSR2

    Currently, we do not ignore any signals we catch, though debatably
    SIGHUP (terminal died), SIGQUIT (core dump), SIGUSR1, and SIGUSR2
    should be ignored.
    """

    def __init__(self, cleanup_callback: Callable[[int], None] | None = None) -> None:
        """Basic constructor. Signal listeners are set up on constructor call.

        Parameters:

        cleanup_callback: This is an optional callback function which will be
        called once a signal is caught. The callback function takes in a single
        integer parameter, which will be the signal code intercepted.

        """
        self._exit = Event()
        self._cleanup_callback = cleanup_callback
        catch_signals = [
            signal.SIGINT,
            signal.SIGTERM,
        ]
        if sys.platform != 'win32':
            catch_signals += [
                signal.SIGHUP,
                signal.SIGQUIT,
                signal.SIGUSR1,
                signal.SIGUSR2,
            ]
        for signum in catch_signals:
            signal.signal(signum, self._on_signal_caught)

    def _on_signal_caught(self, signal: int, _: Any) -> None:
        """Executes when signal is caught.

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
        """Determine if signal has been detected. Useful as the "while" condition for application loops.

        Returns:
        True if signal has been detected, False otherwise
        """
        return self._exit.is_set()

    def stop(self) -> None:
        """Manually stop this SignalHandler, without actually sending the OS signal."""
        self._exit.set()

    def wait(self, amount: float) -> None:
        """While a signal has not been called, block for "amount" seconds.

        If a signal is caught, the "wait" function is immediately interrupted.

        Params:
          amount: time to block
        """
        self._exit.wait(amount)


def default_intersect_lifecycle_loop(
    intersect_gateway: IntersectClient | IntersectService,
    delay: float = 30.0,
    post_startup_callback: Callable[[], None] | None = None,
    cleanup_callback: Callable[[int], None] | None = None,
    waiting_callback: Callable[[IntersectClient | IntersectService], None] | None = None,
) -> None:
    """If users don't have their own lifecycle manager, they can import this function to begin a lifecycle loop.

    This loop automatically catches appropriate OS signals and allows for graceful shutdown.

    IMPORTANT: If you are integrating an INTERSECT adapter into your existing application, you should use your
    own application's lifecycle manager instead.

    Params:
      - intersect_gateway: This can be either an IntersectClient or an IntersectService.
      - delay: how often the loop should wait for (default: 30 seconds)
      - post_startup_callback: Optional callback function which is called after service startup, once.
        The callback function provides no parameters.
        This can be useful if you want to start up some event-emitting threads inside your capability,
        which you should only do AFTER you've connected to the brokers.
      - cleanup_callback: This is an optional callback function which will be
        called once a signal is caught. The callback function takes in a single
        integer parameter, which will be the signal code intercepted. The function
        will be executed just before the loop ends.
      - waiting_callback: This is an optional callback function which will be
        called every <DELAY> seconds. It takes in the adapter, and returns nothing.
        This can be useful to set for debugging purposes.

    """
    sighandler = SignalHandler(cleanup_callback=cleanup_callback)
    intersect_gateway.startup()
    if post_startup_callback:
        post_startup_callback()
    logger.debug('INTERSECT: starting default loop')
    while not sighandler.should_stop():
        if intersect_gateway.considered_unrecoverable():
            die('Application in unrecoverable state.')
        sighandler.wait(delay)
        if waiting_callback:
            waiting_callback(intersect_gateway)
    intersect_gateway.shutdown(reason='Application gracefully terminated.')

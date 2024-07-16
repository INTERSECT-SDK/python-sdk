from __future__ import annotations

from typing import Callable


class TopicHandler:
    """ControlPlaneManager information about a topic, avoids protocol specific information."""

    callbacks: set[Callable[[bytes], None]]
    """Set of functions to call when consuming a message.

    (In practice there will only be one callback, but it could be helpful to add a debugging function callback in for development.)
    """
    topic_persist: bool
    """Whether or not a topic queue is expected to persist on the message broker."""

    def __init__(self, topic_persist: bool) -> None:
        self.callbacks = set()
        self.topic_persist = topic_persist

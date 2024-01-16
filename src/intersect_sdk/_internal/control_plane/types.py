from typing import Callable, DefaultDict, Set

TOPIC_TO_HANDLER_TYPE = DefaultDict[str, Set[Callable[[bytes], None]]]
GET_TOPIC_TO_HANDLER_TYPE = Callable[[], TOPIC_TO_HANDLER_TYPE]

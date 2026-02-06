from collections.abc import Callable

MessageCallback = Callable[[bytes, str, dict[str, str]], None]
"""
All subscription callback functions take three arguments, provided by the protocol handler:

1. The PAYLOAD of the message, in raw bytes.
2. The content-type of the PAYLOAD (as a valid utf-8 string). This can be validated prior to the callback function.
3. A UTF-8 mapping of header keys to header values. These should generally be specific to a domain, and will get validated in the callback function.
"""

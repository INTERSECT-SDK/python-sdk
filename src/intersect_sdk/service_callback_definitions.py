"""Callback definitions used by Services and Capabilities.

Please see shared_callback_definitions for definitions which are also used by Clients.
"""

from typing import Callable

from .client_callback_definitions import INTERSECT_JSON_VALUE

INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE = Callable[[INTERSECT_JSON_VALUE], None]
"""Callback typing for the function which handles another Service's response.

The function accepts one argument - the direct response from the other Service. Message metadata will not be included.

This callback type should only be used on Capabilities - for client callback functions, use INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE .
"""

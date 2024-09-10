"""Callback definitions used by Services and Capabilities.

Please see shared_callback_definitions for definitions which are also used by Clients.
"""

from typing import Callable

from .shared_callback_definitions import INTERSECT_JSON_VALUE

INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE = Callable[[str, str, bool, INTERSECT_JSON_VALUE], None]
"""Callback typing for the function which handles another Service's response.

Params
  The SDK will send the function four arguments:
    1) The message source - this is mostly useful for your own control flow loops you write in the function
    2) The name of the operation that triggered the response from your ORIGINAL message - needed for your own control flow loops if sending multiple messages.
    3) A boolean - if True, there was an error; if False, there was not.
    4) The response, as a Python object - the type should be based on the corresponding Service's schema response.
       The Python object will already be deserialized for you. If parameter 3 was "True", then this will be the error message, as a string.
       If parameter 3 was "False", then this will be either an integer, boolean, float, string, None,
       a List[T], or a Dict[str, T], where "T" represents any of the 7 aforementioned types.

This callback type should only be used on Capabilities - for client callback functions, use INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE .
"""

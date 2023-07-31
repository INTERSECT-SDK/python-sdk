# flake8: noqa

import sys as _sys

from . import handlers as _handlers
from . import pb_derivatives as _pb_derivatives

# Default serializer/de-serializers that can be called
serialize = _handlers.JsonHandler.serialize
deserialize = _handlers.JsonHandler.deserialize

__all__ = ["serialize", "deserialize"]

# Add all of the message types to the package namespace.
# Need a pointer to the module itself which can be used when calling setattr()
# This also appends the packages to __all__ in case 'import *' is used.
_self = _sys.modules[__name__]
for _ii in _pb_derivatives.valid_message_types:
    setattr(_self, _ii.__name__, _ii)
    __all__.append(_ii.__name__)

# Add all of the handlers to the package namespace.
_self = _sys.modules[__name__]
for _ii in _handlers.valid_serialization_handlers:
    setattr(_self, _ii.__name__, _ii)
    __all__.append(_ii.__name__)

# Clean up variables that aren't needed
del _ii
del _self

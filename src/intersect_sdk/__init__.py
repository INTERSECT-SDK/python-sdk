"""The root module contains the intended public API for users of the INTERSECT-SDK.

Users should not need to import anything outside of the root.

In general, most breaking changes on version updates will relate to:
  - Configuration classes (both adding and removing new config models). These configuration classes are relevant to the next point.
  - When a new data service is integrated into INTERSECT, ALL adapters will need to update to support this data service, which will include new dependencies.
"""

from importlib import import_module
from typing import TYPE_CHECKING

# import everything eagerly for IDEs/LSPs
if TYPE_CHECKING:
    from intersect_sdk_common import (
        ControlPlaneConfig,
        ControlProvider,
        DataStoreConfig,
        DataStoreConfigMap,
        HierarchyConfig,
        IntersectDataHandler,
        IntersectMimeType,
    )

    from .app_lifecycle import default_intersect_lifecycle_loop
    from .capability.base import IntersectBaseCapabilityImplementation
    from .client import IntersectClient
    from .client_callback_definitions import (
        INTERSECT_CLIENT_EVENT_CALLBACK_TYPE,
        INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE,
        IntersectClientCallback,
    )
    from .config.client import IntersectClientConfig
    from .config.service import IntersectServiceConfig
    from .exceptions import IntersectCapabilityError
    from .schema import get_schema_from_capability_implementations
    from .service import IntersectService
    from .service_callback_definitions import (
        INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
    )
    from .service_definitions import (
        IntersectEventDefinition,
        intersect_message,
        intersect_status,
    )
    from .shared_callback_definitions import (
        INTERSECT_JSON_VALUE,
        INTERSECT_RESPONSE_VALUE,
        IntersectDirectMessageParams,
        IntersectEventMessageParams,
    )
    from .version import __version__, version_info, version_string

__all__ = (
    'INTERSECT_CLIENT_EVENT_CALLBACK_TYPE',
    'INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE',
    'INTERSECT_JSON_VALUE',
    'INTERSECT_RESPONSE_VALUE',
    'INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE',
    'ControlPlaneConfig',
    'ControlProvider',
    'DataStoreConfig',
    'DataStoreConfigMap',
    'HierarchyConfig',
    'IntersectBaseCapabilityImplementation',
    'IntersectCapabilityError',
    'IntersectClient',
    'IntersectClientCallback',
    'IntersectClientConfig',
    'IntersectDataHandler',
    'IntersectDirectMessageParams',
    'IntersectEventDefinition',
    'IntersectEventMessageParams',
    'IntersectMimeType',
    'IntersectService',
    'IntersectServiceConfig',
    '__version__',
    'default_intersect_lifecycle_loop',
    'get_schema_from_capability_implementations',
    'intersect_message',
    'intersect_status',
    'version_info',
    'version_string',
)

# PEP 562 stuff: do lazy imports for people who just want to import from the top-level module
# [0] = package, [1] = path to module within package
__lazy_imports = {
    # COMMON: core types
    'IntersectDataHandler': ('intersect_sdk_common', ''),
    'IntersectMimeType': ('intersect_sdk_common', ''),
    # COMMON: config types
    'ControlPlaneConfig': ('intersect_sdk_common', ''),
    'ControlProvider': ('intersect_sdk_common', ''),
    'DataStoreConfig': ('intersect_sdk_common', ''),
    'DataStoreConfigMap': ('intersect_sdk_common', ''),
    'HierarchyConfig': ('intersect_sdk_common', ''),
    # imports not in common
    'INTERSECT_CLIENT_EVENT_CALLBACK_TYPE': (__spec__.parent, '.client_callback_definitions'),
    'INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE': (__spec__.parent, '.client_callback_definitions'),
    'INTERSECT_JSON_VALUE': (__spec__.parent, '.shared_callback_definitions'),
    'INTERSECT_RESPONSE_VALUE': (__spec__.parent, '.shared_callback_definitions'),
    'INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE': (__spec__.parent, '.service_callback_definitions'),
    'IntersectBaseCapabilityImplementation': (__spec__.parent, '.capability.base'),
    'IntersectCapabilityError': (__spec__.parent, '.exceptions'),
    'IntersectClient': (__spec__.parent, '.client'),
    'IntersectClientCallback': (__spec__.parent, '.client_callback_definitions'),
    'IntersectClientConfig': (__spec__.parent, '.config.client'),
    'IntersectDirectMessageParams': (__spec__.parent, '.shared_callback_definitions'),
    'IntersectEventDefinition': (__spec__.parent, '.service_definitions'),
    'IntersectEventMessageParams': (__spec__.parent, '.shared_callback_definitions'),
    'IntersectService': (__spec__.parent, '.service'),
    'IntersectServiceConfig': (__spec__.parent, '.config.service'),
    '__version__': (__spec__.parent, '.version'),
    'default_intersect_lifecycle_loop': (__spec__.parent, '.app_lifecycle'),
    'get_schema_from_capability_implementations': (__spec__.parent, '.schema'),
    'intersect_message': (__spec__.parent, '.service_definitions'),
    'intersect_status': (__spec__.parent, '.service_definitions'),
    'version_info': (__spec__.parent, '.version'),
    'version_string': (__spec__.parent, '.version'),
}


def __getattr__(attr_name: str) -> object:
    attr_module = __lazy_imports.get(attr_name)
    if attr_module:
        module = import_module(attr_module[1], package=attr_module[0])
        return getattr(module, attr_name)

    msg = f'module {__name__!r} has no attribute {attr_name!r}'
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return list(__all__)

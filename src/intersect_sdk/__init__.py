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
    from .config.shared import (
        ControlPlaneConfig,
        ControlProvider,
        DataStoreConfig,
        DataStoreConfigMap,
        HierarchyConfig,
    )
    from .core_definitions import IntersectDataHandler, IntersectMimeType
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

__lazy_imports = {
    'INTERSECT_CLIENT_EVENT_CALLBACK_TYPE': '.client_callback_definitions',
    'INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE': '.client_callback_definitions',
    'INTERSECT_JSON_VALUE': '.shared_callback_definitions',
    'INTERSECT_RESPONSE_VALUE': '.shared_callback_definitions',
    'INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE': '.service_callback_definitions',
    'ControlPlaneConfig': '.config.shared',
    'ControlProvider': '.config.shared',
    'DataStoreConfig': '.config.shared',
    'DataStoreConfigMap': '.config.shared',
    'HierarchyConfig': '.config.shared',
    'IntersectBaseCapabilityImplementation': '.capability.base',
    'IntersectCapabilityError': '.exceptions',
    'IntersectClient': '.client',
    'IntersectClientCallback': '.client_callback_definitions',
    'IntersectClientConfig': '.config.client',
    'IntersectDataHandler': '.core_definitions',
    'IntersectDirectMessageParams': '.shared_callback_definitions',
    'IntersectEventDefinition': '.service_definitions',
    'IntersectEventMessageParams': '.shared_callback_definitions',
    'IntersectMimeType': '.core_definitions',
    'IntersectService': '.service',
    'IntersectServiceConfig': '.config.service',
    '__version__': '.version',
    'default_intersect_lifecycle_loop': '.app_lifecycle',
    'get_schema_from_capability_implementations': '.schema',
    'intersect_message': '.service_definitions',
    'intersect_status': '.service_definitions',
    'version_info': '.version',
    'version_string': '.version',
}


def __getattr__(attr_name: str) -> object:
    attr_module = __lazy_imports.get(attr_name)
    if attr_module:
        module = import_module(attr_module, package=__spec__.parent)
        return getattr(module, attr_name)

    msg = f'module {__name__!r} has no attribute {attr_name!r}'
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return list(__all__)

"""The root module contains the intended public API for users of the INTERSECT-SDK.

Users should not need to import anything outside of the root.

In general, most breaking changes on version updates will relate to:
  - Configuration classes (both adding and removing new config models). These configuration classes are relevant to the next point.
  - When a new data service is integrated into INTERSECT, ALL adapters will need to update to support this data service, which will include new dependencies.
"""

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
from .schema import get_schema_from_capability_implementations
from .service import IntersectService
from .service_callback_definitions import (
    INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE,
)
from .service_definitions import (
    IntersectEventDefinition,
    intersect_event,
    intersect_message,
    intersect_status,
)
from .shared_callback_definitions import (
    INTERSECT_JSON_VALUE,
    IntersectDirectMessageParams,
)
from .version import __version__, version_info, version_string

__all__ = [
    'IntersectDataHandler',
    'IntersectEventDefinition',
    'IntersectMimeType',
    'intersect_event',
    'intersect_message',
    'intersect_status',
    'get_schema_from_capability_implementations',
    'IntersectService',
    'IntersectClient',
    'IntersectClientCallback',
    'IntersectDirectMessageParams',
    'INTERSECT_CLIENT_RESPONSE_CALLBACK_TYPE',
    'INTERSECT_CLIENT_EVENT_CALLBACK_TYPE',
    'INTERSECT_JSON_VALUE',
    'INTERSECT_SERVICE_RESPONSE_CALLBACK_TYPE',
    'IntersectBaseCapabilityImplementation',
    'default_intersect_lifecycle_loop',
    'IntersectClientConfig',
    'IntersectServiceConfig',
    'HierarchyConfig',
    'ControlPlaneConfig',
    'ControlProvider',
    'DataStoreConfig',
    'DataStoreConfigMap',
    '__version__',
    'version_info',
    'version_string',
]

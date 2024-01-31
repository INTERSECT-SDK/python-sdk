"""The root module contains the intended public API for users of the INTERSECT-SDK.

Users should not need to import anything outside of the root.

In general, most breaking changes on version updates will relate to:
  - Configuration classes (both adding and removing new config models). These configuration classes are relevant to the next point.
  - When a new data service is integrated into INTERSECT, ALL adapters will need to update to support this data service, which will include new dependencies.
"""

from .annotations import (
    IntersectDataHandler,
    IntersectMimeType,
    intersect_message,
    intersect_status,
)
from .app_lifecycle import default_intersect_lifecycle_loop
from .client import (
    INTERSECT_CLIENT_CALLBACK_TYPE,
    INTERSECT_JSON_VALUE,
    IntersectClient,
    IntersectClientMessageParams,
)
from .config.client import IntersectClientConfig
from .config.service import IntersectServiceConfig
from .config.shared import (
    ControlPlaneConfig,
    DataStoreConfig,
    DataStoreConfigMap,
    HierarchyConfig,
)
from .schema import get_schema_from_model
from .service import IntersectService
from .version import __version__, version_info

__all__ = [
    'IntersectDataHandler',
    'IntersectMimeType',
    'intersect_message',
    'intersect_status',
    'get_schema_from_model',
    'IntersectService',
    'IntersectClient',
    'IntersectClientMessageParams',
    'INTERSECT_CLIENT_CALLBACK_TYPE',
    'INTERSECT_JSON_VALUE',
    'default_intersect_lifecycle_loop',
    'IntersectClientConfig',
    'IntersectServiceConfig',
    'HierarchyConfig',
    'ControlPlaneConfig',
    'DataStoreConfig',
    'DataStoreConfigMap',
    '__version__',
    'version_info',
]

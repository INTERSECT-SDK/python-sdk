from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, NamedTuple
from uuid import UUID

# Common Types use in Capability Definitions
IntersectFilepath     = Path
IntersectTimeDuration = timedelta
IntersectTimeStamp    = datetime
IntersectUUID         = UUID

class IntersectKeyVal(NamedTuple):
    key   : str
    value : str

# Special Values of Common Types
INTERSECT_INVALID_UUID   : IntersectUUID = UUID(int=0)
INTERSECT_NAMESPACE_UUID : IntersectUUID = UUID(hex='494E5445-5253-4543-5421-000000000000') # hex for ASCII 'INTERSECT!'

@dataclass
class IntersectParameterInfo:
    param_name        : str
    param_description : str
    param_type        : str
    default_value     : str
    permitted_values  : List[str]

# Intersect Entities and Relationships

@dataclass
class IntersectEntity:
    entity_uuid         : IntersectUUID
    entity_name         : str
    entity_type         : str
    entity_description  : str
    entity_labels       : List[str]
    entity_properties   : List[str]
    #entity_properties   : List[IntersectKeyVal]

@dataclass
class IntersectEntityRelation:
    relation_name       : str
    source_id           : IntersectUUID
    target_id           : IntersectUUID
    relation_properties : List[str]
    #relation_properties   : List[IntersectKeyVal]

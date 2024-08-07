
from datetime import datetime, timezone
from typing import Dict, Generic, List, Union

import neo4j

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectService,
    intersect_message
)

from capability_catalog.capability_types import (
    IntersectUUID, INTERSECT_INVALID_UUID,
    IntersectEntity, IntersectEntityRelation
)

from capability_catalog.utility.availability_status.types import (
    AvailabilityStatusEnum,
    AvailabilityStatus
)

from capability_catalog.data.er_catalog.types import (
    ERCatalogCapabilityResult,
    CreateEntityCommand, RemoveEntityCommand,
    CreateRelationCommand, RemoveRelationCommand,
    GetEntityInformationRequest, GetEntityInformationReply,
    GetEntityRelationshipsRequest, GetEntityRelationshipsReply,
    GetEntitySourceRelationshipsRequest, GetEntitySourceRelationshipsReply,
    GetEntityTargetRelationshipsRequest, GetEntityTargetRelationshipsReply,
    GetSourceEntitiesByRelationRequest, GetSourceEntitiesByRelationReply,
    GetTargetEntitiesByRelationRequest, GetTargetEntitiesByRelationReply,
    GetEntitiesByTypeRequest, GetEntitiesByTypeReply,
    GetEntitiesByLabelRequest, GetEntitiesByLabelReply,
    GetEntitiesByPropertyRequest, GetEntitiesByPropertyReply
)

from capability_catalog.system.system_manager.types import (
    EnableServiceCommand, DisableServiceCommand,
    RegisterServiceRequest
)

class ERCatalogCapability(IntersectBaseCapabilityImplementation):
    """ A prototype graph database implementation of the INTERSECT 'Entity-Relation Catalog' microservice capability """
        
    def __init__(self, service_hierarchy : HierarchyConfig) -> None:
        super().__init__()
        self.capability_name = "EntityRelationCatalog"

        # Private Data
        self._service_desc    : str = "Provides an entity-relationship catalog."
        self._service_name    : str = service_hierarchy.service
        self._system_name     : str = service_hierarchy.system
        self._subsys_name     : str = "data-management"
        self._org_name        : str = service_hierarchy.organization
        self._facility_name   : str = service_hierarchy.facility

        self._current_status : str = AvailabilityStatusEnum.UNKNOWN
        self._prior_status : str = AvailabilityStatusEnum.UNKNOWN
        self._last_update_description : str = ""
        self._last_update_time : datetime = datetime.now(timezone.utc)
        self._capability_status : str = f'ERCatalogCapability - {self._current_status}'

        self._iservice : IntersectService = None

        # neo4j setup
        neo_uri = "bolt://localhost:7687"
        neo_user = "neo4j"
        neo_pass = "intersect"

        try:
            self._neo = neo4j.GraphDatabase.driver(neo_uri, auth=(neo_user, neo_pass))
            self._neo.verify_connectivity()
            self._set_availability_status(new_status=AvailabilityStatusEnum.AVAILABLE,
                                          description=f'Connected to {neo_uri}')
        except Exception as e:
            self._neo.close()
            error = f'Neo4j connection to "{neo_uri}" raised exception: {repr(e)}'
            print(error)
            self._current_status = AvailabilityStatusEnum.UNAVAILABLE
            self._set_availability_status(new_status=AvailabilityStatusEnum.UNAVAILABLE,
                                          description=error)

    def get_capability_status(self) -> AvailabilityStatus:
        self.update_capability_status()
        curr_status = AvailabilityStatus(current_status=self._current_status,
                                         previous_status=self._prior_status,
                                         status_description=self._capability_status,
                                         status_change_time=self._last_update_time)
        return curr_status

    def update_capability_status(self) -> None:
        self._capability_status = f'ERCatalogCapability - {self._current_status} @ {self._last_update_time} : {self._last_update_description}'

    def startup(self, svc : IntersectService) -> None:
        self._iservice = svc

    # Private Methods
    
    def _set_availability_status(self,
                                 new_status : str,
                                 description : str) -> None:
        # update state
        utcnow = datetime.now(timezone.utc)
        self._prior_status = self._current_status
        self._current_status = new_status
        if description is not None:
            self._last_update_description = description
        self._last_update_time = utcnow

    def _create_entity(self,
                       entity : IntersectEntity) -> bool:
        eid = str(entity.entity_uuid)
        try:
            query = f'MATCH (e WHERE e._uuid = "{eid}") RETURN e._uuid AS uuid'
            record = self._neo.execute_query(query,
                                             result_transformer_=neo4j.Result.single)
            if record is None:
                labels = f'{entity.entity_type}'
                if entity.entity_labels is not None and len(entity.entity_labels) > 0:
                    labels += ':' + ':'.join(entity.entity_labels)
                
                all_props = {
                    "_name": entity.entity_name,
                    "_type": entity.entity_type,
                    "_desc": entity.entity_description,
                    "_uuid": eid,
                }
                if entity.entity_properties is not None and len(entity.entity_properties) > 0:
                    for prop in entity.entity_properties:
                        kv_list = prop.split('=')
                        if len(kv_list) == 2:
                            all_props[kv_list[0]] = kv_list[1]
                
                query = f'CREATE (e:{labels} $props) RETURN e._uuid AS uuid'
                record = self._neo.execute_query(query, {"props": all_props},
                                                 result_transformer_=neo4j.Result.single)
            if record is not None:
                if record["uuid"] == str(entity.entity_uuid):
                    return True
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return False
    
    def _remove_entity(self,
                       entity_uuid : IntersectUUID) -> bool:
        eid = str(entity_uuid)
        query = f'MATCH (e WHERE e._uuid = "{eid}") DETACH DELETE e'
        try:
            _, summary, _ = self._neo.execute_query(query)
            if summary.counters.nodes_deleted == 1:
                return True
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return False
    
    def _create_relation(self,
                         relation : IntersectEntityRelation) -> bool:
        rel_name = relation.relation_name
        src = self._get_entity_by_uuid(relation.source_id)
        dst = self._get_entity_by_uuid(relation.target_id)
        if src is not None and dst is not None:
            try:
                query =  f'MATCH (src:{src.entity_type} {{_uuid: "{src.entity_uuid}"}})'
                query += f' MATCH (dst:{dst.entity_type} {{_uuid: "{dst.entity_uuid}"}})'
                query += f' MATCH (src)-[r:{rel_name}]->(dst) RETURN type(r) AS rname'
                record = self._neo.execute_query(query, result_transformer_=neo4j.Result.single)
                if record is None:
                    have_props = False
                    if relation.relation_properties is not None and len(relation.relation_properties) > 0:
                        have_props = True
                        rel_props = dict()
                        rel_props_map = "{"
                        for prop in relation.relation_properties:
                            kv_list = prop.split('=')
                            if len(kv_list) == 2:
                                key = kv_list[0]
                                val = kv_list[1]
                                rel_props[key] = val
                                rel_props_map += f'{key}: $relprops.{key}, '
                        rel_props_map += "}"
                        rel_props_map = rel_props_map.replace(', }', '}')

                    
                    query =  f'MATCH (src:{src.entity_type} {{_uuid: "{src.entity_uuid}"}})'
                    query += f' MATCH (dst:{dst.entity_type} {{_uuid: "{dst.entity_uuid}"}})'
                    if have_props:
                        query += f' CREATE (src)-[r:{rel_name} {rel_props_map}]->(dst)'
                    else:
                        query += f' CREATE (src)-[r:{rel_name}]->(dst)'
                    query += ' RETURN type(r) AS rname'
        
                    if have_props:
                        record = self._neo.execute_query(query, {"relprops": rel_props},
                                                        result_transformer_=neo4j.Result.single)
                    else:
                        record = self._neo.execute_query(query, result_transformer_=neo4j.Result.single)
                
                if record is not None:
                    if record["rname"] == rel_name:
                        return True
                    else:
                        print(f'DEBUG: relation name {rel_name} mismatch, record is {record}')
                else:
                    print(f'Neo4j query "{query}" returned no record')
            except Exception as e:
                print(f'Neo4j query "{query}" raised exception:', repr(e))
        else:
            print('DEBUG: lookup of source and target entities for relation failed')
        return False
    
    def _remove_relation(self,
                         relation_name : str,
                         source_uuid   : IntersectUUID,
                         target_uuid   : IntersectUUID) -> bool:
        src = self._get_entity_by_uuid(source_uuid)
        dst = self._get_entity_by_uuid(target_uuid)
        if src is not None and dst is not None:
            query =  f'MATCH (src:{src.entity_type} {{_uuid: "{src.entity_uuid}"}})'
            query += f' MATCH (dst:{dst.entity_type} {{_uuid: "{dst.entity_uuid}"}})'
            query += f' MATCH (src)-[r:{relation_name}]->(dst) DELETE r'
            try:
                _, summary, _ = self._neo.execute_query(query)
                if summary.counters.relationships_deleted == 1:
                    return True
            except Exception as e:
                print(f'Neo4j query "{query}" raised exception:', repr(e))
        else:
            print('DEBUG: lookup of source and target entities for relation failed')
        return False

    def _get_entity_by_uuid(self,
                            uuid : IntersectUUID) -> Union[IntersectEntity, None]:
        eid = str(uuid)
        query = f'MATCH (e WHERE e._uuid = "{eid}") RETURN e._name, e._desc, e._type'
        try:
            record = self._neo.execute_query(query,
                                             routing_=neo4j.RoutingControl.READ,
                                             result_transformer_=neo4j.Result.single)
            if record is not None:
                entity = IntersectEntity(entity_uuid=uuid,
                                         entity_name=record["e._name"],
                                         entity_type=record["e._type"],
                                         entity_description=record["e._desc"],
                                         entity_labels=list(),
                                         entity_properties=list())
                return entity
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entity_labels_by_uuid(self,
                                   uuid : IntersectUUID) -> Union[List[str], None]:
        eid = str(uuid)
        query = f'MATCH (e WHERE e._uuid = "{eid}") RETURN e._type, labels(e)'
        try:
            record = self._neo.execute_query(query,
                                             routing_=neo4j.RoutingControl.READ,
                                             result_transformer_=neo4j.Result.single)
            if record is not None:
                labels : List[str] = record["labels(e)"]
                etyp = record["e._type"]
                if etyp in labels:
                    labels.remove(record["e._type"])
                return labels
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entity_properties_by_uuid(self,
                                       uuid : IntersectUUID) -> Union[Dict, None]:
        eid = str(uuid)
        query = f'MATCH (e WHERE e._uuid = "{eid}") RETURN e'
        try:
            record = self._neo.execute_query(query,
                                             routing_=neo4j.RoutingControl.READ,
                                             result_transformer_=neo4j.Result.single)
            if record is not None:
                properties : dict = record["e"]
                if "_name" in properties:
                    del properties["_name"]
                if "_type" in properties:
                    del properties["_type"]
                if "_uuid" in properties:
                    del properties["_uuid"]
                if "_desc" in properties:
                    del properties["_desc"]
                return properties
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entity_source_relations(self,
                                     entity   : IntersectEntity,
                                     relation : str = None) -> Union[List[IntersectEntityRelation], None]:
        eid = str(entity.entity_uuid)
        etyp = entity.entity_type
        if relation is None or len(relation) == 0:
            query = f'MATCH (src:{etyp} WHERE src._uuid = "{eid}")-[r]->(dst)'
        else:
            query = f'MATCH (src:{etyp} WHERE src._uuid = "{eid}")-[r:{relation}]->(dst)'
        query += ' RETURN src._uuid AS src_uuid, dst._uuid AS dst_uuid, type(r) AS rname'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                ier = IntersectEntityRelation(relation_name=record["rname"],
                                              source_id=IntersectUUID(record["src_uuid"]),
                                              target_id=IntersectUUID(record["dst_uuid"]),
                                              relation_properties=list())
                matches.append(ier)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entity_target_relations(self,
                                     entity   : IntersectEntity,
                                     relation : str = None) -> Union[List[IntersectEntityRelation], None]:
        eid = str(entity.entity_uuid)
        etyp = entity.entity_type
        if relation is None or len(relation) == 0:
            query = f'MATCH (src)-[r]->(dst:{etyp} WHERE dst._uuid = "{eid}")'
        else:
            query = f'MATCH (src)-[r:{relation}]->(dst:{etyp} WHERE dst._uuid = "{eid}")'
        query += ' RETURN src._uuid AS src_uuid, dst._uuid AS dst_uuid, type(r) AS rname'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                ier = IntersectEntityRelation(relation_name=record["rname"],
                                              source_id=IntersectUUID(record["src_uuid"]),
                                              target_id=IntersectUUID(record["dst_uuid"]),
                                              relation_properties=list())
                matches.append(ier)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_relation_sources(self,
                              relation : str) -> Union[List[IntersectUUID], None]:
        query = f'MATCH (src)-[r:{relation}]->(dst) RETURN src._uuid as uuid'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                uuid = IntersectUUID(record["uuid"])
                matches.append(uuid)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_relation_targets(self,
                              relation : str) -> Union[List[IntersectUUID], None]:
        query = f'MATCH (src)-[r:{relation}]->(dst) RETURN dst._uuid as uuid'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                uuid = IntersectUUID(record["uuid"])
                matches.append(uuid)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entities_by_type(self,
                              type : str) -> Union[List[IntersectUUID], None]:
        query = f'MATCH (e:{type}) RETURN e._uuid as uuid'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                uuid = IntersectUUID(record["uuid"])
                matches.append(uuid)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entities_by_label(self,
                               label : str) -> Union[List[IntersectUUID], None]:
        query = f'MATCH (e:{label}) RETURN e._uuid as uuid'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                uuid = IntersectUUID(record["uuid"])
                matches.append(uuid)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
    
    def _get_entities_by_property(self,
                                  property : str,
                                  value_expr : str = None) -> Union[List[IntersectUUID], None]:
        query = f'MATCH (e WHERE e.{property} = {value_expr}) RETURN e._uuid as uuid'
        try:
            records, _, _ = self._neo.execute_query(query,
                                                    routing_=neo4j.RoutingControl.READ)
            matches = list()
            for record in records:
                uuid = IntersectUUID(record["uuid"])
                matches.append(uuid)
            return matches
        except Exception as e:
            print(f'Neo4j query "{query}" raised exception:', repr(e))
        return None
        
    # Interactions

    @intersect_message()
    def create_entity(self, params: CreateEntityCommand) -> ERCatalogCapabilityResult:
        entity = params.entity
        result = self._create_entity(entity)
        return ERCatalogCapabilityResult(success=result)

    @intersect_message()
    def remove_entity(self, params: RemoveEntityCommand) -> ERCatalogCapabilityResult:
        entity_uuid = params.entity_id
        result = self._remove_entity(entity_uuid)
        return ERCatalogCapabilityResult(success=result)
    
    @intersect_message()
    def create_relation(self, params: CreateRelationCommand) -> ERCatalogCapabilityResult:
        relation = params.relation
        result = self._create_relation(relation)
        return ERCatalogCapabilityResult(success=result)

    @intersect_message()
    def remove_relation(self, params: RemoveRelationCommand) -> ERCatalogCapabilityResult:
        result = self._remove_relation(relation_name=params.relation_name,
                                       source_uuid=params.source_id,
                                       target_uuid=params.target_id)
        return ERCatalogCapabilityResult(success=result)

    @intersect_message()
    def get_entity_information(self, params: GetEntityInformationRequest) -> GetEntityInformationReply:
        info = self._get_entity_by_uuid(uuid=params.entity_id)
        if info is not None:
            return GetEntityInformationReply(entity_info=info, error="")
        else:
            return GetEntityInformationReply(entity_info=None, error="Entity Not Found")

    @intersect_message()
    def get_entity_relationships(self, params: GetEntityRelationshipsRequest) -> GetEntityRelationshipsReply:
        relations = list()
        info = self._get_entity_by_uuid(uuid=params.entity_id)
        if info is None:
            return GetEntityRelationshipsReply(relationships=relations, error="Entity Not Found")
        else:
            src_list = self._get_entity_source_relations(entity=info, relation=params.relation_name)
            if src_list is not None:
                relations.extend(src_list)
            dst_list = self._get_entity_target_relations(entity=info, relation=params.relation_name)
            if dst_list is not None:
                relations.extend(dst_list)
            return GetEntityRelationshipsReply(relationships=relations, error="")
        
    @intersect_message()
    def get_entity_source_relationships(self, params: GetEntitySourceRelationshipsRequest) -> GetEntitySourceRelationshipsReply:
        relations = list()
        info = self._get_entity_by_uuid(uuid=params.entity_id)
        if info is None:
            return GetEntitySourceRelationshipsReply(relationships=relations, error="Entity Not Found")
        else:
            src_list = self._get_entity_source_relations(entity=info, relation=params.relation_name)
            if src_list is not None:
                relations.extend(src_list)
            return GetEntitySourceRelationshipsReply(relationships=relations, error="")
        
    @intersect_message()
    def get_entity_target_relationships(self, params: GetEntityTargetRelationshipsRequest) -> GetEntityTargetRelationshipsReply:
        relations = list()
        info = self._get_entity_by_uuid(uuid=params.entity_id)
        if info is None:
            return GetEntityTargetRelationshipsReply(relationships=relations, error="Entity Not Found")
        else:
            dst_list = self._get_entity_target_relations(entity=info, relation=params.relation_name)
            if dst_list is not None:
                relations.extend(dst_list)
            return GetEntityTargetRelationshipsReply(relationships=relations, error="")
        
    @intersect_message()
    def get_source_entities_by_relation(self, params: GetSourceEntitiesByRelationRequest) -> GetSourceEntitiesByRelationReply:
        sources = self._get_relation_sources(relation=params.relation_name)
        if sources is None:
            return GetSourceEntitiesByRelationReply(sources=sources, error="Relation Not Found")
        else:
            return GetSourceEntitiesByRelationReply(sources=sources, error="")
        
    @intersect_message()
    def get_target_entities_by_relation(self, params: GetTargetEntitiesByRelationRequest) -> GetTargetEntitiesByRelationReply:
        targets = self._get_relation_targets(relation=params.relation_name)
        if targets is None:
            return GetTargetEntitiesByRelationReply(targets=targets, error="Relation Not Found")
        else:
            return GetTargetEntitiesByRelationReply(targets=targets, error="")
        
    @intersect_message()
    def get_entities_by_type(self, params: GetEntitiesByTypeRequest) -> GetEntitiesByTypeReply:
        entities = self._get_entities_by_type(type=params.type)
        if entities is None:
            return GetEntitiesByTypeReply(entities=entities, error="Type Not Found")
        else:
            return GetEntitiesByTypeReply(entities=entities, error="")
        
    @intersect_message()
    def get_entities_by_label(self, params: GetEntitiesByLabelRequest) -> GetEntitiesByLabelReply:
        entities = self._get_entities_by_label(label=params.label)
        if entities is None:
            return GetEntitiesByLabelReply(entities=entities, error="Label Not Found")
        else:
            return GetEntitiesByLabelReply(entities=entities, error="")
        
    @intersect_message()
    def get_entities_by_property(self, params: GetEntitiesByPropertyRequest) -> GetEntitiesByPropertyReply:
        entities = self._get_entities_by_property(property=params.property, value_expr=params.value_expression)
        if entities is None:
            return GetEntitiesByPropertyReply(entities=entities, error="Property Not Found")
        else:
            return GetEntitiesByPropertyReply(entities=entities, error="")

if __name__ == '__main__':
    print("This is a service implementation module. It is not meant to be executed.")

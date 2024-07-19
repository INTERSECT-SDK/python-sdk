import os
import tempfile
import warnings

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Generic, List, Union
from uuid import UUID

from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectClientMessageParams,
    IntersectService,
    intersect_message
)

from capability_catalog.capability_types import IntersectUUID, IntersectKeyVal

from capability_catalog.utility.availability_status.types import (
    AvailabilityStatusEnum,
    AvailabilityStatus
)

from capability_catalog.system.system_manager.types import (
    EnableServiceCommand, DisableServiceCommand,
    RegisterServiceRequest
)

from capability_catalog.data.data_storage.types import (
    DataStorageCapabilityResult,
    DataStorageCapabilityStatus,
    DataCollectionDetails, DataItemDetails, DataNamespaceDetails,
    CreateDataCollectionCommand,
    CreateDataItemFromLocalFileCommand,
    CreateDataItemFromBytesCommand,
    CreateDataNamespaceCommand,
    RemoveDataCollectionCommand,
    RemoveDataItemCommand,
    RemoveDataNamespaceCommand,
    UpdateDataItemCommand,
    GetDataCollectionDetailsRequest, GetDataCollectionDetailsReply,
    GetDataItemAsBytesRequest, GetDataItemAsBytesReply,
    GetDataItemAsLocalFileRequest, GetDataItemAsLocalFileReply,
    GetDataItemDetailsRequest, GetDataItemDetailsReply,
    GetDataNamespaceDetailsRequest, GetDataNamespaceDetailsReply,
    ListDataCollectionsRequest, ListDataCollectionsReply,
    ListDataItemsRequest, ListDataItemsReply,
    ListDataNamespacesReply,
    DataCollectionCreation, DataCollectionRemoval,
    DataItemCreation, DataItemUpdate, DataItemRemoval,
    DataNamespaceCreation, DataNamespaceRemoval
)

class FileDataStorageCapability(IntersectBaseCapabilityImplementation):
    """ A prototype file-based implementation of the INTERSECT 'Data Storage' microservice capability """

    # Internal Metadata Classes

    @dataclass
    class DataNamespaceMeta:
        name             : str
        create_time      : datetime
        fs_path          : Path
        total_bytes      : int
        data_collections : Dict
        data_items       : Dict

    @dataclass
    class DataCollectionMeta:
        name        : str
        namespace   : str
        create_time : datetime
        fs_path     : Path
        total_bytes : int
        data_items  : Dict
        properties  : List[IntersectKeyVal] = None

    @dataclass
    class DataItemMeta:
        name        : str
        namespace   : str
        create_time : datetime
        update_time : datetime
        fs_path     : Path
        item_bytes  : int
        collection  : str = None
        local_file  : Path = None
        properties  : List[IntersectKeyVal] = None
        
    def __init__(self, service_hierarchy : HierarchyConfig) -> None:
        super().__init__()
        self.capability_name = "DataStorage"

        # Private Data
        self._service_desc    : str = "Manages file-based storage for the local INTERSECT system."
        self._service_name    : str = service_hierarchy.service
        self._system_name     : str = service_hierarchy.system
        self._subsys_name     : str = "data-management"
        self._org_name        : str = service_hierarchy.organization
        self._facility_name   : str = service_hierarchy.facility

        self._current_status : str = AvailabilityStatusEnum.UNKNOWN
        self._prior_status : str = AvailabilityStatusEnum.UNKNOWN
        self._last_update_description : str = ""
        self._last_update_time : datetime = datetime.now(timezone.utc)
        self._capability_status : str = f'FileDataStorageCapability - {self._current_status}'
        
        self._namespaces = dict()

        self._iservice : IntersectService = None

        tmp_dir = Path(tempfile.gettempdir())
        self._data_dir = tmp_dir / "data"
        self._create_fs_dir(self._data_dir)
        self._tmpfile_dir = tmp_dir / "tmp"
        self._create_fs_dir(self._tmpfile_dir)

    def get_capability_status(self) -> AvailabilityStatus:
        curr_status = AvailabilityStatus(current_status=self._current_status,
                                         previous_status=self._prior_status,
                                         status_description=self._last_update_description,
                                         status_change_time=self._last_update_time)
        return curr_status

    def startup(self, svc : IntersectService) -> None:
        self._iservice = svc

        # use local service to finish initialization
        system_manager = f'{self._org_name}.{self._facility_name}.{self._system_name}.infrastructure-management.system-manager'
        register_request = \
            IntersectClientMessageParams(
                destination=system_manager,
                operation='SystemManager.register_service',
                payload=RegisterServiceRequest(service_name=self._service_name,
                                               subsystem_name=self._subsys_name,
                                               service_description=self._service_desc,
                                               service_capabilities=[self.capability_name],
                                               service_resources=list(),
                                               service_labels=list(),
                                               service_properties=list())
            )
        enable_request = \
            IntersectClientMessageParams(
                destination=system_manager,
                operation='SystemManager.enable_service',
                payload=EnableServiceCommand(service_id=UUID(int=0),
                                             service_name=self._service_name,
                                             change_description="STARTUP")
            )
        self._iservice.add_startup_messages([(register_request, None),
                                             (enable_request, None)])

        disable_request = \
            IntersectClientMessageParams(
                destination=system_manager,
                operation='SystemManager.disable_service',
                payload=DisableServiceCommand(service_id=UUID(int=0),
                                              service_name=self._service_name,
                                              change_description="SHUTDOWN")
            )
        self._iservice.add_shutdown_messages([(disable_request, None)])

    
    # Private Methods

    def _create_fs_dir(self, fs_dir : Path) -> bool:
        if not fs_dir.exists():
            fs_dir.mkdir(parents=True)
            return True
        else:
            return False

    def _delete_fs_dir(self, fs_dir : Path) -> bool:
        if fs_dir.exists() and fs_dir.is_dir():
            fs_dir.rmdir()
            return True
        else:
            return False

    def _create_fs_file_from_bytes(self, fs_file : Path, contents : bytes) -> bool:
        if not fs_file.exists():
            fs_file.touch()
        fs_file.write_bytes(contents)
        return True

    def _create_fs_file_by_copy(self, fs_file : Path, existing_file : Path) -> bool:
        if existing_file.exists():
            if not fs_file.exists():
                fs_file.touch()
            fs_file.write_bytes(existing_file.read_bytes())
            return True
        else:
            return False

    def _delete_fs_file(self, fs_file : Path) -> bool:
        if fs_file.exists():
            fs_file.unlink()
            return True
        else:
            return False

    def _get_namespace(self, ns : str) -> Union[DataNamespaceMeta, None]:
        ns_meta = None
        if ns in self._namespaces:
            ns_meta = self._namespaces[ns]
        else:
            err = f'Data namespace "{ns}" does not exist!'
            warnings.warn(err)
        return ns_meta

    def _get_collection(self, ns : str, coll : str) -> Union[DataCollectionMeta, None]:
        coll_meta = None
        if ns in self._namespaces:
            ns_meta = self._namespaces[ns]
            if coll in ns_meta.data_collections:
                coll_meta = ns_meta.data_collections[coll]
            else:
                err = f'Data collection "{ns}.{coll}" does not exist!'
                warnings.warn(err)
        return coll_meta

    def _get_item(self, ns : str, item : str, coll : str = None) -> Union[DataItemMeta, None]:
        item_meta = None
        if ns in self._namespaces:
            ns_meta = self._namespaces[ns]
            if coll is not None and len(coll) > 0:
                if coll in ns_meta.data_collections:
                    coll_meta = ns_meta.data_collections[coll]
                    if item in coll_meta.data_items:
                        item_meta = coll_meta.data_items[item]
                else:
                    err = f'Data collection "{ns}.{coll}" does not exist!'
                    warnings.warn(err)
            elif item in ns_meta.data_items:
                item_meta = ns_meta.data_items[item]
        return item_meta

    def _remove_item(self, item_meta : DataItemMeta) -> DataItemDetails:
        item_details = DataItemDetails(item_name=item_meta.name,
                                       item_namespace=item_meta.namespace,
                                       item_collection=item_meta.collection,
                                       item_data_size=item_meta.item_bytes,
                                       item_create_time=item_meta.create_time,
                                       item_update_time=item_meta.update_time,
                                       item_properties=item_meta.properties)
        if item_meta.fs_path.exists():
            bytes_removed = item_meta.fs_path.stat().st_size
            if bytes_removed != item_details.item_data_size:
                item_details.item_data_size = bytes_removed
            self._delete_fs_file(item_meta.fs_path)
        return item_details

    def _remove_collection(self, coll_meta : DataCollectionMeta) -> DataCollectionDetails:
        bytes_removed = 0
        coll_details = DataCollectionDetails(coll_name=coll_meta.name,
                                             coll_namespace=coll_meta.namespace,
                                             coll_item_count=len(coll_meta.data_items),
                                             coll_data_size=coll_meta.total_bytes,
                                             coll_create_time=coll_meta.create_time,
                                             coll_properties=coll_meta.properties)
        for item in coll_meta.data_items.values():
            item_details = self._remove_item(item)
            bytes_removed += item_details.item_data_size
        self._delete_fs_dir(coll_meta.fs_path)
        if bytes_removed != coll_details.coll_data_size:
            coll_details.coll_data_size = bytes_removed
        return coll_details

    def _remove_namespace(self, ns_meta : DataNamespaceMeta) -> DataNamespaceDetails:
        bytes_removed = 0
        ns_details = DataNamespaceDetails(ns_name=ns_meta.name,
                                          ns_coll_count=len(ns_meta.data_collections),
                                          ns_item_count=len(ns_meta.data_items),
                                          ns_create_time=ns_meta.create_time)
        for coll in ns_meta.data_collections.values():
            coll_details = self._remove_collection(coll)
            bytes_removed += coll_details.coll_data_size
            ns_details.ns_item_count += coll_details.coll_item_count
        for item in ns_meta.data_items.values():
            item_details = self._remove_item(item)
            bytes_removed += item_details.item_data_size
        self._delete_fs_dir(ns_meta.fs_path)
        ns_details.ns_data_size = bytes_removed
        return ns_details

    def update_capability_status(self) -> None:
        n_ns = len(self._namespaces)
        self._capability_status = f'FileDataStorageCapability - {self._current_status} (# namespaces = {n_ns})'

    # Interactions

    @intersect_message()
    def create_data_namespace(self, params: CreateDataNamespaceCommand) -> DataStorageCapabilityResult:
        if params.ns_name not in self._namespaces:
            ns_dir = self._data_dir / params.ns_name
            if self._create_fs_dir(ns_dir):
                self._namespaces[params.ns_name] = \
                    self.DataNamespaceMeta(name=params.ns_name,
                                           create_time=datetime.now(timezone.utc),
                                           fs_path=ns_dir,
                                           total_bytes=0,
                                           data_collections=dict(),
                                           data_items=dict())
                return DataStorageCapabilityResult(success=True)
            else:
                err = f'Filesystem directory "{ns_dir}" already exists!'
                warnings.warn(err)
        else:
            err = f'Data namespace "{params.ns_name}" already exists!'
            warnings.warn(err)
        return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def create_data_collection(self, params: CreateDataCollectionCommand) -> DataStorageCapabilityResult:
        if params.coll_namespace in self._namespaces:
            ns_meta = self._namespaces[params.coll_namespace]
            coll_dir = self._data_dir / params.coll_namespace / params.coll_name
            if self._create_fs_dir(coll_dir):
                ns_meta.data_collections[params.coll_name] = \
                    self.DataCollectionMeta(name=params.coll_name,
                                            namespace=params.coll_namespace,
                                            create_time=datetime.now(timezone.utc),
                                            fs_path=coll_dir,
                                            total_bytes=0,
                                            data_items=dict(),
                                            properties=params.coll_properties)
                return DataStorageCapabilityResult(success=True)
            else:
                err = f'Filesystem directory "{coll_dir}" already exists!'
                warnings.warn(err)
        else:
            err = f'Data namespace "{params.coll_namespace}" does not exist!'
            warnings.warn(err)
        return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def create_data_item_from_bytes(self, params: CreateDataItemFromBytesCommand) -> DataStorageCapabilityResult:
        if params.item_namespace in self._namespaces:
            ns_meta = self._namespaces[params.item_namespace]
            item_path = self._data_dir / params.item_namespace / params.item_name
            coll_meta = None
            if len(params.item_collection):
                if params.item_collection in ns_meta.data_collections:
                    coll_meta = ns_meta.data_collections[params.item_collection]
                    item_path = self._data_dir / params.item_namespace / params.item_collection / params.item_name
                else:
                    err = f'Data collection "{params.item_namespace}.{params.item_collection}" not found!'
                    warnings.warn(err)
                    return DataStorageCapabilityResult(success=False)

            if self._create_fs_file_from_bytes(fs_file=item_path, contents=params.item_contents):
                item_sz = len(params.item_contents)
                item_meta = self.DataItemMeta(name=params.item_name,
                                              namespace=params.item_namespace,
                                              collection=params.item_collection,
                                              create_time=datetime.now(timezone.utc),
                                              update_time=datetime.now(timezone.utc),
                                              fs_path=item_path,
                                              item_bytes=item_sz,
                                              properties=params.item_properties)
                if coll_meta is not None:
                    coll_meta.data_items[params.item_name] = item_meta
                    coll_meta.total_bytes += item_sz
                else:
                    ns_meta.data_items[params.item_name] = item_meta
                ns_meta.total_bytes += item_sz
                return DataStorageCapabilityResult(success=True)
            else:
                err = f'File create for "{params.item_name}" failed!'
                warnings.warn(err)
                return DataStorageCapabilityResult(success=False)
        else:
            err = f'Data namespace "{params.item_namespace}" not found!'
            warnings.warn(err)
            return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def create_data_item_from_local_file(self, params: CreateDataItemFromLocalFileCommand) -> DataStorageCapabilityResult:
        local_file = Path(params.local_file_path)
        if not local_file.exists():
            err = f'Local file "{params.local_file_path}" does not exist!'
            warnings.warn(err)
            return DataStorageCapabilityResult(success=False)
        else:
            if params.item_namespace in self._namespaces:
                ns_meta = self._namespaces[params.item_namespace]
                item_path = self._data_dir / params.item_namespace / params.item_name
                coll_meta = None
                if len(params.item_collection):
                    if params.item_collection in ns_meta.data_collections:
                        coll_meta = ns_meta.data_collections[params.item_collection]
                        item_path = self._data_dir / params.item_namespace / params.item_collection / params.item_name
                    else:
                        err = f'Data collection "{params.item_namespace}.{params.item_collection}" not found!'
                        warnings.warn(err)
                        return DataStorageCapabilityResult(success=False)

                if self._create_fs_file_by_copy(fs_file=item_path, existing_file=local_file):
                    local_sz = local_file.stat().st_size
                    item_meta = self.DataItemMeta(name=params.item_name,
                                                  namespace=params.item_namespace,
                                                  collection=params.item_collection,
                                                  create_time=datetime.now(timezone.utc),
                                                  update_time=datetime.now(timezone.utc),
                                                  fs_path=item_path,
                                                  item_bytes=local_sz,
                                                  local_file=local_file,
                                                  properties=params.item_properties)
                    if coll_meta is not None:
                        coll_meta.data_items[params.item_name] = item_meta
                        coll_meta.total_bytes += len(local_sz)
                    else:
                        ns_meta.data_items[params.item_name] = item_meta
                    ns_meta.total_bytes += len(local_sz)
                    return DataStorageCapabilityResult(success=True)
                else:
                    err = f'File create for "{params.item_name}" by copy from "{local_file}" failed!'
                    warnings.warn(err)
                    return DataStorageCapabilityResult(success=False)
            else:
                err = f'Data namespace "{params.item_namespace}" not found!'
                warnings.warn(err)
                return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def remove_data_namespace(self, params: RemoveDataNamespaceCommand) -> DataStorageCapabilityResult:
        if params.ns_name in self._namespaces:
            ns_meta = self._namespaces.pop(params.ns_name)
            ns_details = self._remove_namespace(ns_meta)
            # TODO - generate DataNamespaceRemoval(ns_details) status event
            return DataStorageCapabilityResult(success=True)
        else:
            err = f'Data namespace "{params.ns_name}" does not exist!'
            warnings.warn(err)
            return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def remove_data_collection(self, params: RemoveDataCollectionCommand) -> DataStorageCapabilityResult:
        if params.coll_namespace in self._namespaces:
            ns_meta = self._namespaces[params.coll_namespace]
            if params.coll_name in ns_meta.data_collections:
                coll_meta = ns_meta.data_collections.pop(params.coll_name)
                coll_details = self._remove_collection(coll_meta)
                ns_meta.total_bytes -= coll_details.coll_data_size
                # TODO - generate DataCollectionRemoval(coll_details) status event
                return DataStorageCapabilityResult(success=True)
            else:
                err = f'Data collection "{params.coll_namespace}.{params.coll_name}" does not exist!'
                warnings.warn(err)
                return DataStorageCapabilityResult(success=False)
        else:
            err = f'Data namespace "{params.coll_namespace}" not found!'
            warnings.warn(err)
            return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def remove_data_item(self, params: RemoveDataItemCommand) -> DataStorageCapabilityResult:
        if params.item_namespace in self._namespaces:
            ns_meta = self._namespaces[params.item_namespace]
            item_meta = None
            coll_meta = None
            if len(params.item_collection):
                if params.item_collection in ns_meta.data_collections:
                    coll_meta = ns_meta.data_collections[params.item_collection]
                    if params.item_name in coll_meta.data_items:
                        item_meta = coll_meta.data_items.pop(params.item_name)
                else:
                    err = f'Data collection "{params.item_namespace}.{params.item_collection}" not found!'
                    warnings.warn(err)
                    return DataStorageCapabilityResult(success=False)
            elif params.item_name in ns_meta.data_items:
                item_meta = ns_meta.data_items.pop(params.item_name)

            if item_meta is not None:
                item_sz = item_meta.file_size
                item_details = self._remove_item(fs_file=item_meta.fs_path)
                if item_sz != item_details.item_data_size:
                    item_sz = item_details.item_data_size
                    err = f'Mismatch on data item size for "{params.item_name}"!'
                    warnings.warn(err)
                if coll_meta is not None:
                    coll_meta.total_bytes -= item_sz
                ns_meta.total_bytes -= item_sz
                # TODO - generate DataItemRemoval(item_details) status event
                return DataStorageCapabilityResult(success=True)
            else:
                err = f'Data item "{params.item_name}" not found!'
                warnings.warn(err)
                return DataStorageCapabilityResult(success=False)
        else:
            err = f'Data namespace "{params.item_namespace}" not found!'
            warnings.warn(err)
            return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def update_data_item(self, params: UpdateDataItemCommand) -> DataStorageCapabilityResult:
        if params.item_namespace in self._namespaces:
            ns_meta = self._namespaces[params.item_namespace]
            item_meta = None
            coll_meta = None
            if len(params.item_collection):
                if params.item_collection in ns_meta.data_collections:
                    coll_meta = ns_meta.data_collections[params.item_collection]
                    if params.item_name in coll_meta.data_items:
                        item_meta = coll_meta.data_items.get(params.item_name)
                else:
                    err = f'Data collection "{params.item_namespace}.{params.item_collection}" not found!'
                    warnings.warn(err)
                    return DataStorageCapabilityResult(success=False)
            elif params.item_name in ns_meta.data_items:
                item_meta = ns_meta.data_items.get(params.item_name)

            if item_meta is None:
                err = f'Data item "{params.item_name}" does not exist!'
                warnings.warn(err)
                return DataStorageCapabilityResult(success=False)

            if item_meta.local_file is not None:
                item_sz = item_meta.file_size
                local_sz = item_meta.local_file.stat().st_size
                if self._create_fs_file_by_copy(fs_file=item_meta.fs_path,
                                                existing_file=item_meta.local_file):
                    if coll_meta is not None:
                        coll_meta.total_bytes -= item_sz
                        coll_meta.total_bytes += local_sz
                    ns_meta.total_bytes -= item_sz
                    ns_meta.total_bytes += local_sz
                    # TODO - generate DataItemUpdate(item_details) status event
                    return DataStorageCapabilityResult(success=True)
                else:
                    err = f'Data item update for "{params.item_name}" failed!'
                    warnings.warn(err)
                    return DataStorageCapabilityResult(success=False)
        else:
            err = f'Data namespace "{params.item_namespace}" not found!'
            warnings.warn(err)
            return DataStorageCapabilityResult(success=False)

    @intersect_message()
    def get_data_namespace_details(self, params: GetDataNamespaceDetailsRequest) -> GetDataNamespaceDetailsReply:
        details = None
        ns_meta = self._get_namespace(ns=params.ns_name)
        if ns_meta is not None:
            details = DataNamespaceDetails(ns_name=ns_meta.name,
                                           ns_coll_count=len(ns_meta.data_collections),
                                           ns_item_count=len(ns_meta.data_items),
                                           ns_data_size=ns_meta.total_bytes,
                                           ns_create_time=ns_meta.create_time)
            return GetDataNamespaceDetailsReply(ns_details=details, error="")
        else:
            return GetDataNamespaceDetailsReply(ns_details=details, error="Namespace Not Found")

    @intersect_message()
    def get_data_collection_details(self, params: GetDataCollectionDetailsRequest) -> GetDataCollectionDetailsReply:
        details = None
        coll_meta = self._get_collection(ns=params.coll_namespace, coll=params.coll_name)
        if coll_meta is not None:
            details = DataCollectionDetails(coll_name=coll_meta.name,
                                            coll_namespace=params.coll_namespace,
                                            coll_item_count=len(coll_meta.data_items),
                                            coll_data_size=coll_meta.total_bytes,
                                            coll_create_time=coll_meta.create_time,
                                            coll_properties=coll_meta.properties)
            return GetDataCollectionDetailsReply(coll_details=details, error="")
        else:
            return GetDataCollectionDetailsReply(coll_details=details, error="Collection Not Found")

    @intersect_message()
    def get_data_item_details(self, params: GetDataItemDetailsRequest) -> GetDataItemDetailsReply:
        details = None
        item_meta = self._get_item(ns=params.item_namespace, item=params.item_name, coll=params.item_collection)
        if item_meta is not None:
            details = DataItemDetails(item_name=item_meta.name,
                                      item_namespace=params.item_namespace,
                                      item_collection=params.item_collection,
                                      item_data_size=item_meta.item_bytes,
                                      item_create_time=item_meta.create_time,
                                      item_update_time=item_meta.update_time,
                                      item_properties=item_meta.properties)
            return GetDataItemDetailsReply(item_details=details, error="")
        else:
            return GetDataItemDetailsReply(item_details=details, error="Item Not Found")

    @intersect_message()
    def get_data_item_as_bytes(self, params: GetDataItemAsBytesRequest) -> GetDataItemAsBytesReply:
        contents = None
        item_meta = self._get_item(ns=params.item_namespace, item=params.item_name, coll=params.item_collection)
        if item_meta is not None:
            contents = item_meta.fs_path.read_bytes()
            return GetDataItemAsBytesReply(item_contents=contents, error="")
        else:
            return GetDataItemAsBytesReply(item_contents=bytes(), error="Item Not Found")

    @intersect_message()
    def get_data_item_as_local_file(self, params: GetDataItemAsLocalFileRequest) -> GetDataItemAsLocalFileReply:
        item_meta = self._get_item(ns=params.item_namespace, item=params.item_name, coll=params.item_collection)
        if item_meta is not None:
            fd, tmp_file_path = tempfile.mkstemp(dir=self._tmpfile_dir)
            os.close(fd)
            if self._create_fs_file_by_copy(fs_file=tmp_file_path, existing_file=item_meta.fs_path):
                return GetDataItemAsLocalFileReply(local_file_path=tmp_file_path, is_temp_file=True)
            else:
                return GetDataItemAsLocalFileReply(error="Failed to create temporary file!")
        else:
            return GetDataItemAsLocalFileReply(error="Item Not Found")

    @intersect_message()
    def list_data_namespaces(self) -> ListDataNamespacesReply:
        ns_list = list(self._namespaces.keys())
        return ListDataNamespacesReply(ns_names=ns_list)

    @intersect_message()
    def list_data_collections(self, params: ListDataCollectionsRequest) -> ListDataCollectionsReply:
        ns_meta = self._get_namespace(ns=params.ns_name)
        if ns_meta is not None:
            coll_list = list(ns_meta.data_collections.keys())
            return ListDataCollectionsReply(coll_names=coll_list, error="")
        else:
            err = f'Data namespace "{params.ns_name}" not found!'
            warnings.warn(err)
            return ListDataCollectionsReply(coll_names=list(), error=err)

    @intersect_message()
    def list_data_items(self, params: ListDataItemsRequest) -> ListDataItemsReply:
        if len(params.coll_name) == 0:
            ns_meta = self._get_namespace(ns=params.ns_name)
            if ns_meta is not None:
                item_list = list(ns_meta.data_items.keys())
                return ListDataItemsReply(ns_name=params.ns_name,
                                          coll_name=params.coll_name,
                                          item_names=item_list, error="")
            else:
                err = f'Data namespace "{params.ns_name}" not found!'
                warnings.warn(err)
                return ListDataItemsReply(ns_name=params.ns_name,
                                          coll_name=params.coll_name,
                                          item_names=list(), error=err)
        else:
            coll_meta = self._get_collection(ns=params.ns_name, coll=params.coll_name)
            if coll_meta is not None:
                item_list = list(coll_meta.data_items.keys())
                return ListDataItemsReply(ns_name=params.ns_name,
                                          coll_name=params.coll_name,
                                          item_names=item_list, error="")
            else:
                err = f'Data collection "{params.coll_name}" not found!'
                warnings.warn(err)
                return ListDataItemsReply(ns_name=params.ns_name,
                                          coll_name=params.coll_name,
                                          item_names=list(), error=err)

if __name__ == '__main__':
    print("This is a service implementation module. It is not meant to be executed.")

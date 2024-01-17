import random
from typing import Any, Union

from ...annotations import IntersectDataHandler, IntersectMimeType
from ...config.shared import DataStoreConfigMap, HierarchyConfig
from ..exceptions import IntersectException
from ..logger import logger
from ..messages.userspace import UserspaceMessage
from .minio_utils import MinioPayload, create_minio_store, get_minio_object, send_minio_object


class DataPlaneManager:
    """
    The DataPlaneManager serves as a common interface to the data plane
    """

    def __init__(self, hierarchy: HierarchyConfig, data_configs: DataStoreConfigMap) -> None:
        """
        Params:
          hierarchy: Hierarchy configuration
          data_configs: data configuration
        """
        self._hierarchy = hierarchy
        self._minio_providers = list(map(create_minio_store, data_configs.minio))

    def incoming_message_data_handler(self, message: UserspaceMessage) -> Union[str, bytes, None]:
        """
        Get data from the request data provider

        Params:
          message: the message sent externally to this location
        Returns:
          the actual data we want to submit to the user function
        Raise:
          IntersectException - if we couldn't get the data
        """
        request_data_handler = message['headers']['data_handler']
        if request_data_handler == IntersectDataHandler.MESSAGE:
            return message['payload'] if message['payload'] else None
        if request_data_handler == IntersectDataHandler.MINIO:
            payload: MinioPayload = message['payload']
            provider = None
            for store in self._minio_providers:
                if store._base_url._url.geturl() == payload['minio_url']:  # noqa: SLF001 (only way to get URL from MINIO API)
                    provider = store
                    break
            if not provider:
                logger.error(
                    f"You did not configure listening to MINIO instance '{payload['minio_url']}'. You must fix this to handle this data."
                )
                raise IntersectException
            return get_minio_object(provider, payload)
        logger.warning(f'Cannot parse data handler {request_data_handler}')
        raise IntersectException

    def outgoing_message_data_handler(
        self,
        function_response: bytes,
        content_type: IntersectMimeType,
        data_handler: IntersectDataHandler,
    ) -> Any:
        """
        Send the user's response to the appropriate data provider

        Params:
          - function_response - the return value from the user's function
          - content_type - content type of function_response
          - data_handler - where we're going to send the data off to (i.e. the message, MINIO...)
        Returns:
          the payload of the message
        Raise:
          IntersectException - if there was any error in submitting the response
        """
        # TODO - instead of requiring users to specify the data handler themselves, another idea could be to use
        # sys.getsizeof(function_response) and determine the data handler dynamically
        # users could perhaps specify T1/T2/T3 data types but not the specific implementation
        if data_handler == IntersectDataHandler.MESSAGE:
            return function_response.decode()
        if data_handler == IntersectDataHandler.MINIO:
            provider = random.choice(self._minio_providers)  # noqa: S311 (TODO choose a MINIO provider better than at random)
            return send_minio_object(function_response, provider, content_type, self._hierarchy)

        logger.error(
            f'No support implemented for code {data_handler}, please upgrade your intersect-sdk version.'
        )
        raise IntersectException
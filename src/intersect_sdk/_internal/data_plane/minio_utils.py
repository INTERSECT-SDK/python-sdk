import mimetypes
from hashlib import sha224
from io import BytesIO
from uuid import uuid4

from minio import Minio
from minio.error import MinioException
from typing_extensions import TypedDict
from urllib3.exceptions import MaxRetryError
from urllib3.util import parse_url

from ...config.shared import DataStoreConfig, HierarchyConfig
from ...core_definitions import IntersectMimeType
from ..exceptions import IntersectError
from ..logger import logger
from ..utils import die


class MinioPayload(TypedDict):
    """This is a payload which gets sent in the actual userspace message if the data handler is "MINIO"."""

    minio_url: str
    """
    The complete URL of the MINIO instance. This is used for finding the correct MINIO instance when retrieving an object.
    """
    minio_bucket: str
    """
    The name of the bucket where the object is located. Each service should only create objects in one bucket.
    """
    minio_object_id: str
    """
    The name of the object. This is a random UUID.
    """


def _condense_minio_bucket_name(hierarchy: HierarchyConfig) -> str:
    """Condense a hierarchy string into a string less than 64 characters.

    This function is needed to handle MINIO bucket names. Collisions should be extremely rare,
    and it should be fairly straightforward to identify a specific bucket for MINIO admins.

    Bucket name = first characters (up to 6) of service name + hyphen + sha224 of full hierarchy string

    TODO in the future, MINIO calls should be system-level only, so only the system + facility + organization
    should need to be hashed.
    Also, potentially come up with a better hashing algorithm (though sha224 is compressed enough, and gives us 56 characters).
    """
    return f'{hierarchy.service[:6]}-{sha224(hierarchy.hierarchy_string().encode()).hexdigest()}'


def create_minio_store(config: DataStoreConfig) -> Minio:
    config_uri = parse_url(config.host)
    if not config_uri.host:
        die(f'Minio configuration host {config.host} cannot be parsed as a valid hostname.')

    client = Minio(
        secure=config_uri.scheme == 'https',
        access_key=config.username,
        secret_key=config.password,
        endpoint=config_uri.host if not config.port else f'{config_uri.host}:{config.port}',
    )
    try:
        # it doesn't matter if the bucket exists, we're just checking the exception
        # this is the fastest way in the public API to perform a HEAD request.
        client.bucket_exists('qwop')
    except MinioException:
        die(f'Invalid credentials for Minio instance: {config}')
    return client


def send_minio_object(
    data: bytes, provider: Minio, content_type: IntersectMimeType, hierarchy: HierarchyConfig
) -> MinioPayload:
    """Core function to save data in MINIO.

    Params:
      data: user response data, as bytes
      provider: the Minio client
      content_type: the content type of the body
      hierarchy: the hierarchy configuration
    Returns:
      The MINIO payload which gets sent in the actual message.

    Raises:
      IntersectException - if any non-fatal MinIO error is caught
    """
    bucket_name = _condense_minio_bucket_name(hierarchy)
    # mimetypes.guess_extension() is a nice-to-have for MINIO preview, but isn't essential.
    object_id = str(uuid4()) + (mimetypes.guess_extension(content_type.value) or '')
    try:
        if not provider.bucket_exists(bucket_name):
            provider.make_bucket(bucket_name)
        buff_data = BytesIO(data)
        provider.put_object(
            bucket_name=bucket_name,
            object_name=object_id,
            data=buff_data,
            length=buff_data.getbuffer().nbytes,
            content_type=content_type.value,
        )
        return MinioPayload(
            minio_url=provider._base_url._url.geturl(),  # noqa: SLF001 (only way to get URL from MINIO API)
            minio_bucket=bucket_name,
            minio_object_id=object_id,
        )
    except MaxRetryError as e:
        logger.warning(
            f'Non-fatal MinIO error when sending object, the server may be under stress but you should double-check your configuration. Details: \n{e}'
        )
        raise IntersectError from e
    except MinioException as e:
        logger.error(
            f'Important MinIO error when sending object, this usually indicates a problem with your configuration. Details: \n{e}'
        )
        raise IntersectError from e


def get_minio_object(provider: Minio, payload: MinioPayload) -> bytes:
    """Core function to retrieve data from MINIO.

    Params:
      provider: a pre-cached MinIO provider from the data provider store
      payload: the payload from the message (at this point, the minio_url should exist)

    Returns:
      user response data, as raw bytes
    Raises:
      IntersectException - if any non-fatal MinIO error is caught
    """
    try:
        response = provider.get_object(
            bucket_name=payload['minio_bucket'], object_name=payload['minio_object_id']
        )
        # TODO - objects should ONLY be removed if they are T1
        provider.remove_object(
            bucket_name=payload['minio_bucket'], object_name=payload['minio_object_id']
        )
    except MaxRetryError as e:
        logger.warning(
            f'Non-fatal MinIO error when retrieving object, the server may be under stress but you should double-check your configuration. Details: \n{e}'
        )
        raise IntersectError from e
    except MinioException as e:
        logger.error(
            f'Important MinIO error when retrieving object, this usually indicates a problem with your configuration. Details: \n{e}'
        )
        raise IntersectError from e
    else:
        return response.data

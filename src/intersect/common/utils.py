# Provides common helper functions that are used for multiple
# INTERSECT-SDK microservices.

import itertools
import json

# Standard
from datetime import datetime

from .logger import logger


def parse_message_arguments(arguments: str, load: bool = False) -> dict:
    """Read the arguments from a message.

    Interprets the contents of a message's payload
    according to the type specified by arguments_parser.

    Args:
        arguments: A string with the encoded payload values of a message.
            If the json contains "minio" as a key, an
            attempt will be made to load data from the MinIO server.

            MinIO messages must be of the form:
            {
                "minio" : {
                    "object_id": minio object id to load,
                    "bucket" : minio bucket to load the object from
                    "service_name": String for the system name the object was originally stored by
                }
            }
        load: A boolean determining whether to load data referenced by ID.
            If it is false, any object identification information will be returned
            in raw form in the dictionary. If it is true, stored objects will be downloaded
            from whatever data storage they are in and returned in the dictionary.
    Returns:
        A dictionary of values taken from arguments.
    """
    err_msg = f"Error parsing message arguments: {arguments}"

    try:
        args = json.loads(arguments)
        logger.debug("message arguments -> %s", args)

        # If we are not to load remote objects,
        # return the arguments as is without trying to interpret them to find stored objects.
        if not load:
            return args

        # No remote data loading currently supported, so return the raw
        # arguments
        return args

    except ValueError as e:
        logger.error(err_msg)
        raise e
    except TypeError as e:
        logger.error(err_msg)
        raise e


def identifier(service_name, start_value=0):
    """Specialized generators for continuously incrementing an identifier"""

    ii = itertools.count(start_value)
    while True:
        yield f"{service_name}{str(next(ii))}"


def get_utc() -> str:
    """
    Gets a string that represents the current UTC date and time. This timestamp
    adheres to the ISO 8601 format.

    Returns:
        String representing current UTC date and time.

    Example:
        >>> get_utc()
        '2022-12-08T15:52:13.841527Z'
    """
    utc = datetime.utcnow().isoformat() + "Z"
    return utc

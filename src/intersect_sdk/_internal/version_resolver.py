from ..core_definitions import IntersectDataHandler
from ..version import version_info, version_string
from .logger import logger


def _resolve_user_version(
    their_version: str,
    their_source: str,
    their_data_handler: IntersectDataHandler,
    our_version: str,
    our_version_info: tuple[int, int, int],
) -> bool:
    """Function which handles version resolution information.

    Separated into private function for testing purposes
    """
    their_version_info = [int(x) for x in their_version.split('.')]

    # logging rules: log "error" if it's definitely our fault, "warning" if it _might_ be our fault
    if their_version_info[0] != our_version_info[0]:
        logger.warning(
            f'Problem with source {their_source}: Major version incompatibility between our SDK version {our_version} and their SDK version {their_version}'
        )
        return False
    if our_version_info[0] == 0 and our_version_info[1] != their_version_info[1]:
        logger.warning(
            f'Problem with source {their_source}: Pre-release minor version incompatibility between our SDK version {our_version} and their SDK version {their_version}'
        )
        return False
    if their_data_handler.value not in [e.value for e in IntersectDataHandler]:
        logger.error(
            f'Problem with source {their_source}: This adapter cannot handle data handler with code "{their_data_handler}", please upgrade to the latest intersect-sdk version.'
        )
        return False
    # NOTE: consider implementing a content-type check here as well

    return True


def resolve_user_version(
    their_version: str, their_source: str, their_data_handler: IntersectDataHandler
) -> bool:
    """This function handles all version compatibilities between our SDK version and an incoming message's SDK version.

    Params
      their_version - version information from headers
      their_source - source information from headers
      their_data_handler - data handler information from headers

    Returns:
      True if version resolution successful, false otherwise
    """
    return _resolve_user_version(
        their_version,
        their_source,
        their_data_handler,
        our_version=version_string,
        our_version_info=version_info,
    )

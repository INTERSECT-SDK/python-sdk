from ..annotations import IntersectDataHandler
from ..version import __version__ as our_version
from ..version import version_info as our_version_info
from .logger import logger
from .messages.userspace import UserspaceMessage


def resolve_user_version(msg: UserspaceMessage) -> bool:
    """
    This function handles all version compatibilities between our SDK version
    and an incoming message's SDK version.

    Params
      msg - message from the orchestrator or another adapter

    Returns
      True if version resolution successful, false otherwise
    """
    their_version = msg['headers']['sdk_version']
    their_version_info = [int(x) for x in their_version.split('.')]

    # logging rules: log "error" if it's definitely our fault, "warning" if it _might_ be our fault
    if their_version_info[0] != our_version_info[0]:
        logger.warning(
            f'Problem with source {msg["headers"]["source"]}: Major version incompatibility between our SDK version {our_version} and their SDK version {their_version}'
        )
        return False
    if our_version_info[0] == 0 and our_version_info[1] != their_version_info[1]:
        logger.warning(
            f'Problem with source {msg["headers"]["source"]}: Pre-release minor version incompatibility between our SDK version {our_version} and their SDK version {their_version}'
        )
        return False
    if msg['headers']['data_handler'] >= len(IntersectDataHandler):
        logger.error(
            f'Problem with source {msg["headers"]["source"]}: This adapter cannot handle data handler with code "{msg["headers"]["data_handler"]}", please upgrade to the latest intersect-sdk version.'
        )
        return False
    # NOTE: consider implementing a content-type check here as well

    return True

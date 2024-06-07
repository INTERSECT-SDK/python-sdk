"""Version sanity checks to make sure that the release version is properly formatted."""


def strip_version_metadata(version: str) -> str:
    """Given a string, do the following.

    1) Strip out pre-release/build-metadata from the string
    2) If the string is missing all of <MAJOR>.<MINOR>.<PATCH>, raise runtime error

    This is necessary because INTERSECT works off of a strict SemVer string and does not understand build metadata.
    """
    import re

    sem_ver = re.search(r'\d+\.\d+\.\d+', version)
    if sem_ver is None:
        msg = 'Package version does not contain a semantic version "<MAJOR>.<MINOR>.<DEBUG>", please fix this'
        raise RuntimeError(msg)
    return sem_ver.group()

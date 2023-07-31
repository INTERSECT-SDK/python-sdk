from os import PathLike
from pathlib import Path
from typing import Callable, Dict, Optional, Union

from pydantic import ValidationError

from .config_models import IntersectConfig
from .exceptions import IntersectConfigParseException


def _parse_json(filearg: Path):
    import json

    try:
        with open(filearg) as f:
            return json.load(f)
    except OSError as e:
        raise IntersectConfigParseException(66, e.strerror)
    except ValueError as e:
        raise IntersectConfigParseException(65, f"Can't parse JSON: {str(e)}")


def _parse_toml(filearg: Path):
    try:
        # check for optional dependency first
        import tomli as toml
    except ImportError:
        try:
            # for python >= 3.11
            import tomllib as toml  # type: ignore
        except ImportError:
            raise IntersectConfigParseException(
                69, "Python 'tomli' or 'tomllib' library not available"
            )

    try:
        with open(filearg, "rb") as f:
            return toml.load(f)
    except OSError as e:
        raise IntersectConfigParseException(66, e.strerror)
    except ValueError as e:
        raise IntersectConfigParseException(65, f"Can't parse TOML: {str(e)}")


def _parse_yaml(filearg: Path):
    try:
        import yaml
    except ImportError:
        raise IntersectConfigParseException(69, "Python YAML library not available")

    from yaml.error import MarkedYAMLError

    try:
        with open(filearg) as f:
            # not "load" - don't allow execution of arbitrary Python code
            return yaml.safe_load(f)
    except OSError as e:
        raise IntersectConfigParseException(66, e.strerror)
    except MarkedYAMLError as e:
        raise IntersectConfigParseException(65, f"Can't parse YAML: {str(e)}")


def load_config_from_dict(config: Dict) -> IntersectConfig:
    """
    Load the INTERSECT configuration from a dictionary.

    Parameters:
        config: configuration (as an unvalidated dictionary)

    Raises:
        IntersectConfigParseException - if the configuration does not meet the schema requirements

    Returns:
        IntersectConfig object
    """
    try:
        return IntersectConfig(**config)
    except ValidationError as e:
        raise IntersectConfigParseException(65, f"INTERSECT Configuration error: {str(e)}")


def load_config_from_file(
    filearg: Union[str, PathLike], callback: Optional[Callable[[Dict], None]] = None
):
    """
    Load the INTERSECT configuration from a file.

    Parameters:
        filepath: the path to the file on your system (note: must be a JSON, YAML, or TOML file)
        callback: optional callback you may provide if you only store
            a partial configuration in the file. The partial configuration will then be returned
            in the callable as a dict, allowing you to manually mutate it
            (i.e. read in the broker password from a separate file)

    Raises:
        IntersectConfigParseException - occurs if the configuration
            cannot be loaded or cannot be parsed

    Returns:
        IntersectConfig object
    """
    filepath = Path(filearg)
    if not filepath.exists():
        raise IntersectConfigParseException(66, "File does not exist")

    # begin filepath parsing - import based on suffix for efficiency
    if filepath.suffix == ".json":  # we do not support JSON-LD or other JSON extensions
        config = _parse_json(filepath)
    elif filepath.suffix == ".toml":
        config = _parse_toml(filepath)
    elif filepath.suffix == ".yaml" or filepath.suffix == ".yml":
        config = _parse_yaml(filepath)
    else:
        raise IntersectConfigParseException(66, "File is not JSON, TOML, or YAML")

    if callback:
        callback(config)

    return load_config_from_dict(config)

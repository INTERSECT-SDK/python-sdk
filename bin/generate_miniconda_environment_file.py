"""
This file generates a Conda environment.yml from pyproject.toml

(prints to stdout)
"""

from itertools import chain
from pathlib import Path

try:
    # python >= 3.11
    import tomllib as toml
except ImportError:
    # python < 3.11
    import tomli as toml

import yaml

# use delimiter which avoids YAML attempting to insert quotes
DEP_DELIMITER = "\\"
BASE_DIR = Path(__file__).absolute().parents[1]

with open(BASE_DIR / "pyproject.toml", "rb") as f:
    pyproject = toml.load(f)

version = pyproject["project"]["version"]
requires_python = pyproject["project"]["requires-python"]
dependencies = pyproject["project"]["dependencies"]
optionals = pyproject["project"]["optional-dependencies"]

conda_environment = {
    "name": "intersect",
    "dependencies": [
        f"python{requires_python}",
        "pip",
        {
            "pip": dependencies
            + [
                f"{DEP_DELIMITER}{item}"
                for sublist in chain(optionals.values())
                for item in sublist
            ]
            + [
                f"intersect=={version}",
                "-e .",
            ]
        },
    ],
}

print(
    f"""# This file was autogenerated from the INTERSECT dependency list.
# Users should feel free to add dependencies as they wish.
# WARNING: removing any dependencies on this list will cause INTERSECT to be non-functional.
# NOTE: Optional dependencies are commented out.

# Use this file to create a conda environment for developing the intersect
# package. Below are some useful conda environment commands.
#
# Create the environment:      conda env create --file environment.yml
# Activate the environment:    conda activate intersect
# Deactivate the environment:  conda deactivate
# Remove the environment:      conda env remove --name intersect

{yaml.dump(conda_environment).replace(f"- {DEP_DELIMITER}", "#- ")}"""
)

# Python SDK for INTERSECT

This repository contains the Python SDK for INTERSECT.

## Documentation

Documentation for the INTERSECT Python SDK is available [here](x). The documentation is generated with [Sphinx](https://www.sphinx-doc.org) from the `docs` directory. See the documentation for more information about installation, usage, and examples of the Python SDK for INTERSECT.

## Quickstart (developers)

This project uses [PDM](https://pdm.fming.dev/latest/) for Python tooling. Install PDM and run `pdm install -G:all`, or `pdm update` if resyncing the repository.

To install pre-commit hooks, run `pdm run pre-commit install` after installation.

Main commands are specified under `tool.pdm.scripts` in `pyproject.toml`

### Docker build instructions

`docker build --target minimal -t intersect-sdk-python .` 

You will only need to rebuild this image if you need to add/update dependencies.

## Adding dependencies

- **Required dependency**: `pdm add <dependency>`
- **Optional dependency**: `pdm add -G <group> <dependency>` 
- **Dev dependency** `pdm add --dev -G <dev-group> <dependency>`

For dev dependencies, please always specify the dev group as one of `lint`, `test`, or `doc`.

## Linting

Run `pdm run lint` to quickly run all linters. The pre-commit hooks will also catch this.

## Testing

`pdm run test` - run tests in standard format
`pdm run test-debug` - run tests allowing debug output (i.e. print statements in tests)

## Examples

Examples are available in the `examples` directory. The examples in the `python-environment` directory should be run using the supplied conda environment while the examples in the `docker-compose` directory are run with Docker compose. See the documentation and the code comments in each example for more information.

## Contributing

Guidelines for contributing to the SDK are given in the documentation. The guidelines provide information about linters, formatters, and style guides that should be used for this project.

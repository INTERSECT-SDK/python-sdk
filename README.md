# Python SDK for INTERSECT

This repository contains the Python SDK for INTERSECT.

## Documentation

Documentation for the INTERSECT Python SDK can be viewed at http://10.64.193.144:30002. The documentation is generated with [Sphinx](https://www.sphinx-doc.org) from the `docs` directory. See the documentation for more information about installation, usage, and examples of the Python SDK for INTERSECT.

## Quickstart (developers)

This project uses [PDM](https://pdm.fming.dev/latest/) for Python tooling. Install PDM and run `pdm install -G:all`, or `pdm update` if resyncing the repository.

To install pre-commit hooks, run `pdm run pre-commit install` after installation.

Main commands are specified under `tool.pdm.scripts` in `pyproject.toml`

### Docker build instructions

`docker build --target minimal -t intersect-sdk-python .`

You will only need to rebuild this image if you need to add/update dependencies.

### Backing services

A lot of INTERSECT functionality requires backing services be spun up. A quick way to do this is to use the docker-compose.yml file at the repository root to do so: `docker compose up -d`.

If you don't want to use this docker-compose file, note that running a full Service or a full Client requires that you are able to connect to at least one broker (AMQP or MQTT) and at least one of _each_ data provider type (currently, just MINIO).

## Adding dependencies

- **Required dependency**: `pdm add <dependency>`
- **Optional dependency**: `pdm add -G <group> <dependency>`
- **Dev dependency** `pdm add --dev -G <dev-group> <dependency>`

For dev dependencies, please always specify the dev group as one of `lint`, `test`, or `doc`.

## Linting

Run `pdm run lint` to quickly run all linters. The pre-commit hooks will also catch this.

## Testing

Note that for the integration and e2e tests, you will need to spin up the docker-compose instance.

`pdm run test-all` - run all tests in standard format.
`pdm run test-all-debug` - run tests allowing debug output (i.e. print statements in tests)
`pdm run test-unit` - run only the unit tests (no backing services required for these)

Tests are run with pytest if you'd like to customize how they are run. The full `pdm run test...` scripts can be found in `pyproject.toml`

## Examples

Examples are available in the `examples` directory. Please see the README.md in the `examples` directory for more information.

## Contributing

Guidelines for contributing to the SDK are given in the documentation. The guidelines provide information about linters, formatters, and style guides that should be used for this project.

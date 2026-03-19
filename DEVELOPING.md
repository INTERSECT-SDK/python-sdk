# Python SDK for INTERSECT

This repository contains the Python SDK for INTERSECT.

## Documentation

Documentation for the INTERSECT Python SDK can be viewed at https://intersect-python-sdk.readthedocs.io/ . The documentation is generated with [Sphinx](https://www.sphinx-doc.org) from the `docs` directory. See the documentation for more information about installation, usage, and examples of the Python SDK for INTERSECT.

## Quickstart (developers)

This project uses UV for Python tooling. For initial setup:

```bash
uv venv .venv
source .venv/bin/activate
uv sync --all-extras --all-groups
uv run pre-commit install
```

### Docker build instructions

`docker build -t intersect-sdk-python .`

You will only need to rebuild this image if you need to add/update dependencies.

### Backing services

A lot of INTERSECT functionality requires backing services be spun up. A quick way to do this is to use the docker-compose.yml file at the repository root to do so: `docker compose up -d`.

If you don't want to use this docker-compose file, note that running a full Service or a full Client requires that you are able to connect to at least one broker (AMQP or MQTT) and at least one of _each_ data provider type (currently, just MINIO).

## Adding dependencies

- **Required dependency**: `uv add <dependency>`
- **Optional dependency**: `uv add <dependency> --optional`
- **Dev dependency** `uv add --dev <dependency>`

Regarding development dependencies:

- install documentation dependencies with `uv add <dependency> --optional docs`

## Linting

- Formatting: `uv run ruff format`
- Linting: `uv run ruff check --fix`
- Type analysis: `uv run mypy src/`

The pre-commit hooks will also lint for you.

## Testing

If you are running the integration tests or the e2e tests, you will need to spin up the docker-compose instance.

`uv run pytest tests/` - run all tests in standard format.
`uv run pytest tests/unit/` - run only the unit tests (no backing services required for these)

## Examples

Examples are available in the `examples` directory. Please see the README.md in the `examples` directory for more information.

## Contributing

Guidelines for contributing to the SDK are given in the documentation. The guidelines provide information about linters, formatters, and style guides that should be used for this project.

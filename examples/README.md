# Examples

This file contains common instructions on how to run each example.

Each example consists of a client application, one or more service applications, and one schema file per service application. The schema file provides information for how a client can interact with a service, but is not actually loaded when running the examples.

## 1: Setting up your backing service environment

INTERSECT requires numerous backing services to function; the simplest way is to use Docker and Docker Compose. There is a `docker-compose.yml` file at the repository root you can use to set up all backing services; the examples are written to use these credentials.

For example, if running from the repository root:

`docker compose up -d`
`docker compose logs -f`
`docker compose down -v`

## 2: Running the INTERSECT applications

The number of terminals you'll need corresponds to the number of `.py` files in the directory. For example, the `hello-world` example has two applications: `hello_service.py` and `hello_client.py` .

You need to start up ALL `_service.py` files before you start up the `_client.py` file.

There are two ways to run the applications: from a Python virtual environment on your machine, and from Docker.

### 2A: Running the INTERSECT applications from Python

See instructions for setting up Python environment at the repository root's README.md.

From there, you can generally run `python -m <PATH_TO_EXAMPLE>.py` .

### 2B: Running the INTERSECT applications from Docker

See instructions for building the INTERSECT-SDK Docker image at the repository root's README.md.

To run an example, use `docker run --rm -it --network host <INTERSECT_SDK_IMAGE> python -m examples/<PATH_TO_EXAMPLE>.py`

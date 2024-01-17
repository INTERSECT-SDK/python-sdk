# Examples

This file contains common instructions on how to run each example.

Each example consists of a client application, one or more service applications, and one schema file per service application. The schema file provides information for how a client can interact with a service, but is not actually loaded when running the examples.

## Dependencies

The only dependency required is `intersect_sdk`. Note that `intersect_sdk` has several optional dependencies, though these should not be required for running any examples.

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

From there, you can generally run `python -m examples.1_hello_world.hello_service` . (replace `1_hello_world.hello_service` with what you want to run)

### 2B: Running the INTERSECT applications from Docker

See instructions for building the INTERSECT-SDK Docker image at the repository root's README.md.

To run an example, use `docker run --rm -it --network host <INTERSECT_SDK_IMAGE> python -m examples.1_hello_world.hello_service`. (replace `1_hello_world.hello_service` with what you want to run)

## Testing AMQP in an example

By default, all examples use MQTT. To test out AMQP, change this block:

```python
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 1883,
                'protocol': 'mqtt3.1.1',
            },
        ],
```

to this next block:

```python
        'brokers': [
            {
                'username': 'intersect_username',
                'password': 'intersect_password',
                'port': 5672,
                'protocol': 'amqp0.9.1',
            },
        ],
```

You will also need to make sure you have the AMQP dependencies installed (`pip install intersect_sdk[amqp]`) in your environment.
This will be installed by default in the provided Docker container, but may be lacking in the default virtual environment.

Integrating with FastAPI
========================

This example showcases how to make your FastAPI Server an INTERSECT Service as well. These ideas can be used with any other framework. The idea is to integrate INTERSECT with FastAPI, not the other way around.

Service walkthrough
-------------------

The below code is an example of what you can initialize with uvicorn.

.. literalinclude:: ../../examples/5_fastapi_example/app/main.py

Client walkthrough
------------------

In this example, the Client is contacting the Service both via the FastAPI POST endpoint (which additionally sends an INTERSECT event) and the request/response mechanism of INTERSECT.
Note that in the code's order of execution, you will first get the request/response back from INTERSECT, then the HTTP response value, and finally the event value from INTERSECT.

.. literalinclude:: ../../examples/5_fastapi_example/fastapi_client.py

Shared code
-----------

.. literalinclude:: ../../examples/5_fastapi_example/app/shared.py

Running it yourself: Using a Python environment
-----------------------------------------------

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # Start the service in your first terminal
   # Runs on port 8000 and 127.0.0.1 by default, change this with --port <PORT> and --host <HOST> respectively (if running in Docker, need to use 0.0.0.0 host)
   python -m examples.5_fastapi_example.fastapi_service

   # Finally, run the client in a second terminal
   # By default this assumes the service runs on port 8000 on host 127.0.0.1,
   python -m examples.5_fastapi_example.fastapi_client

After a few seconds, the output from ``fastapi_client`` will look something like this:

.. code-block:: text

   Origin from INTERSECT
   Origin from FastAPI - HTTP response
   Origin from FastAPI - INTERSECT

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

Running it yourself: Using Docker
---------------------------------

First, you will need to build the latest INTERSECT-SDK image; run the following command from the repository root:

.. code-block:: bash

   docker build -t intersect-sdk .

Then you can run the examples like this:

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # Start the service in your first terminal
   # Runs on port 8000 and 127.0.0.1 by default, change this with --port <PORT> and --host <HOST> respectively (if running in Docker, need to use 0.0.0.0 host)
   docker run --rm -it --name intersect-service --network host intersect-sdk python -m examples.5_fastapi_example.fastapi_service --host 0.0.0.0

   # Finally, run the client in a second terminal
   # By default this assumes the service runs on port 8000 on host 127.0.0.1,
   docker run --rm -it --name intersect-client --network host intersect-sdk python -m examples.5_fastapi_example.fastapi_client --server-host 0.0.0.0

After several seconds, the output from ``fastapi_client`` will look something like this:

.. code-block:: text

   Origin from INTERSECT
   Origin from FastAPI - HTTP response
   Origin from FastAPI - INTERSECT

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

(If you ran Docker in detached mode (``-d``), you can instead run ``docker stop intersect-client``.)

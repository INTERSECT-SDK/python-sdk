Hello world With events
=======================

This is similar to the Hello World example, but calling the Service will also emit a global "hello_event" which can be seen by all Services.
In this example, the Client will first print out the event output, then will print out the targeted response from the Service as in the Hello World example.

To run these locally, you must first make sure that you have all necessary backing services running; see the :doc:`../installation` page for details on how to do this.

Afterwards, you can start the service in one terminal, wait a brief moment, then finally run the client in another terminal.

Service walkthrough
-------------------

.. literalinclude:: ../../examples/1_hello_world_events/hello_service.py

Client walkthrough
------------------

.. literalinclude:: ../../examples/1_hello_world_events/hello_client.py

Running it yourself: Using a Python environment
-----------------------------------------------

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # First, run the service
   python -m examples.1_hello_world_events.hello_service

   # Next, run the client in a separate terminal
   python -m examples.1_hello_world_events.hello_client

After several seconds, the output from ``hello_client`` will be:

.. code-block:: text

   hello_client requested a salutation!
   Hello, hello_client!

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

Running it yourself: Using Docker
---------------------------------

First, you will need to pull the latest INTERSECT-SDK image:

.. code-block:: bash

   docker login code.ornl.gov:4567
   docker pull code.ornl.gov:4567/intersect/sdk/python-sdk/sdk/main:latest

Then you can run the examples like this:

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # First, run the service
   docker run --rm -it --name intersect-service --network host code.ornl.gov:4567/intersect/sdk/python-sdk/sdk/main:latest python -m examples.1_hello_world_events.hello_service

   # Next, run the client in a separate terminal
   docker run --rm -it --name intersect-client --network host code.ornl.gov:4567/intersect/sdk/python-sdk/sdk/main:latest python -m examples.1_hello_world_events.hello_client

After several seconds, the output from ``hello_client`` will be:

.. code-block:: text

   hello_client requested a salutation!
   Hello, hello_client!

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

(If you ran Docker in detached mode (``-d``), you can instead run ``docker stop intersect-client``.)

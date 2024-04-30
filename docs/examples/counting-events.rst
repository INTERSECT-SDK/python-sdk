Counting With Events
====================

This is an example of a Service which doesn't accept requests from clients, but will continually broadcast an event. Clients can subscribe to these events.

In this example, the Service will send out an "increment_counter" event containing a simple integer value every two seconds. The value will always be 3 times greater than the last emitted value.

To run these locally, you must first make sure that you have all necessary backing services running; see the :doc:`../installation` page for details on how to do this.

Afterwards, you can start the service in one terminal, wait a brief moment, then finally run the client in another terminal.

Service walkthrough
-------------------

.. literalinclude:: ../../examples/2_counting_events/counting_service.py

Client walkthrough
------------------

.. literalinclude:: ../../examples/2_counting_events/counting_client.py

Running it yourself: Using a Python environment
-----------------------------------------------

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # First, run the service
   python -m examples.2_counting_events.counting_service

   # Next, run the client in a separate terminal
   python -m examples.2_counting_events.counting_client

After a few seconds, the output from ``counting_client`` will look something like this (the values will be higher if you waited longer between starting the client and the service):

.. code-block:: text

   3
   9
   27

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

You can also run the client again while NOT killing the service; the output will look different from the last time.

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
   docker run --rm -it --name intersect-service --network host code.ornl.gov:4567/intersect/sdk/python-sdk/sdk/main:latest python -m examples.1_hello_world.hello_service

   # Next, run the client in a separate terminal
   docker run --rm -it --name intersect-client --network host code.ornl.gov:4567/intersect/sdk/python-sdk/sdk/main:latest python -m examples.1_hello_world.hello_client

After several seconds, the output from ``counting_client`` will look something like this (the values will be higher if you waited longer between starting the client and the service):

.. code-block:: text

   3
   9
   27

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

You can also run the client again while NOT killing the service; the output will look different from the last time.

(If you ran Docker in detached mode (``-d``), you can instead run ``docker stop intersect-client``.)

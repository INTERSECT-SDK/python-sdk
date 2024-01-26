Counting
========

This is a slightly more complext on how to communicate with the INTERSECT SDK, how to manage state on the service, complex entrypoints on the service, and how to send multiple messages with the client.

The counting_service class has three entrypoints: start_count, stop_count, and reset_count. These entrypoints all return complex responses, and reset_count allows for specifying if the counter should count again or not.

To run these locally, you must first make sure that you have all necessary backing services running; see the :doc:`../installation` page for details on how to do this.

Afterwards, you can start the service in one terminal, wait a brief moment, then finally run the client in another terminal.

Service walkthrough
-------------------

.. literalinclude:: ../../examples/2_counting/counting_service.py

Client walkthrough
------------------

.. literalinclude:: ../../examples/2_counting/counting_client.py

Running it yourself: Using a Python environment
-----------------------------------------------

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # First, run the service
   python -m examples.2_counting.counting_service

   # Next, run the client in a separate terminal
   python -m examples.2_counting.counting_client

After several seconds, the output from ``counting_client`` will look something like this:

.. code-block:: text

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: start_count
   Payload: {'state': {'count': 1, 'counting': True}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: stop_count
   Payload: {'state': {'count': 6, 'counting': False}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: start_count
   Payload: {'state': {'count': 7, 'counting': True}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: reset_count
   Payload: {'count': 10, 'counting': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: reset_count
   Payload: {'count': 6, 'counting': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: start_count
   Payload: {'state': {'count': 1, 'counting': True}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: stop_count
   Payload: {'state': {'count': 4, 'counting': False}, 'success': True}

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

After several seconds, the output from ``counting_client`` will look something like this:

.. code-block:: text

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: start_count
   Payload: {'state': {'count': 1, 'counting': True}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: stop_count
   Payload: {'state': {'count': 6, 'counting': False}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: start_count
   Payload: {'state': {'count': 7, 'counting': True}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: reset_count
   Payload: {'count': 10, 'counting': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: reset_count
   Payload: {'count': 6, 'counting': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: start_count
   Payload: {'state': {'count': 1, 'counting': True}, 'success': True}

   Source: counting-organization.counting-facility.counting-system.counting-subsystem.counting-service
   Operation: stop_count
   Payload: {'state': {'count': 4, 'counting': False}, 'success': True}

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

You can also run the client again while NOT killing the service; the output will look different from the last time.

(If you ran Docker in detached mode (``-d``), you can instead run ``docker stop intersect-client``.)

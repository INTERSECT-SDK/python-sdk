Ping Pong Events
================

This is an example of a Client communicating with two Services, each which emit their own events. It's also an example of how a Client can dynamically start/stop listening to events from a specific Service during its runtime.

In this example, the Ping service advertises "ping" events and the Pong service advertises "pong" events. We listen to one service at a time, and switch services after receiving an event.

To run these locally, you must first make sure that you have all necessary backing services running; see the :doc:`../installation` page for details on how to do this.

Afterwards, you can start the service in one terminal, wait a brief moment, then finally run the client in another terminal.

Service walkthrough
-------------------

There are two Services, but their code does not significantly differ:

---

Ping Service:

.. literalinclude:: ../../examples/3_ping_pong_events/ping_service.py

Pong Service:

.. literalinclude:: ../../examples/3_ping_pong_events/pong_service.py

Both of these Services share some common code:

.. literalinclude:: ../../examples/3_ping_pong_events/service_runner.py

Client walkthrough
------------------

.. literalinclude:: ../../examples/3_ping_pong_events/ping_pong_client.py

Running it yourself: Using a Python environment
-----------------------------------------------

.. code-block:: bash

   # to suppress progress messages and only show stdout, you can add
   # 2>/dev/null
   # to the end of your command on UNIX systems

   # First, start up the ping service in one terminal
   python -m examples.3_ping_pong_events.ping_service

   # Next, start up the pong service in a second terminal
   python -m examples.3_ping_pong_events.pong_service

   # Finally, run the client in a third terminal
   python -m examples.3_ping_pong_events.ping_pong_client

After a few seconds, the output from ``ping_pong_client`` will look something like this:

.. code-block:: text

   ping
   pong
   ping
   pong

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

You can also run the client again while NOT killing the service; the output will look different from the last time.

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

   # First, start up the ping service in one terminal
   docker run --rm -it --name intersect-service --network host intersect-sdk python examples.3_ping_pong_events.ping_service

   # Next, start up the pong service in a second terminal
   docker run --rm -it --name intersect-service --network host intersect-sdk python examples.3_ping_pong_events.pong_service

   # Finally, run the client in a third terminal
   docker run --rm -it --name intersect-service --network host intersect-sdk python examples.3_ping_pong_events.ping_pong_client

After several seconds, the output from ``ping_pong_client`` will look something like this:

.. code-block:: text

   ping
   pong
   ping
   pong

The client will exit automatically; you will have to use Ctrl+C on the terminal running the service process.

You can also run the client again while NOT killing the service; the output will look different from the last time.

(If you ran Docker in detached mode (``-d``), you can instead run ``docker stop intersect-client``.)

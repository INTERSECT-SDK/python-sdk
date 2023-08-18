Client server counting
======================

This is an example of client-server adapters running a background counter process. See the sections below for running the example using Docker compose or from within a Python environment.

Using a Python environment
--------------------------

This section discusses the ``client-server-counting`` example in the ``examples/python-environment`` directory. Follow the steps below for running the example in a virtual environment which was discussed in the :doc:`../installation` section.

First, if a broker is not already running, run the broker in a separate terminal session as discussed on the :doc:`../installation` page.

After starting the broker and activating the virtual environment, run the ``server.py`` in a terminal session as shown below. The server will begin outputting status messages while measuring its uptime and incrementing a count up from 0 every second.

.. code-block:: bash

   python server.py

The output from ``server.py`` should look like the following after several seconds:

.. code-block:: text

   Press Ctrl-C to exit.
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...
   Received request from example-client, sending reply...

Next, run the ``client.py`` in another terminal session. Don't forget to activate the conda environment in this terminal session too. Once run, the client will begin to stop and start the server's count while also requesting its current value.

.. code-block:: bash

   python client.py

The output from ``client.py`` should look like the following after several seconds:

.. code-block:: text

   Press Ctrl-C to exit.
   Count received from server: 4
   Received request from example-server, sending reply...
   Count received from server: 4
   Received request from example-server, sending reply...
   Count received from server: 9
   Received request from example-server, sending reply...
   Count received from server: 10
   Received request from example-server, sending reply...

Using Docker compose
--------------------

Coming soon.

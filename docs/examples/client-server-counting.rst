Client server counting
======================

This is an example of client-server adapters running a background counter process. See the sections below for running the example using Docker compose or from within a Python environment.

Using a Python environment
--------------------------

This section discusses the ``client-server-counting`` example in the ``examples/python-environment`` directory. Follow the steps below for running the example in a conda environment.

First, if a broker is not already running, run the broker in a separate terminal session as discussed on the :doc:`../installation` page.

Next, in another terminal session, run the following commands to use the ``environment.yml`` file to create a conda environment for this example:

.. code-block:: bash

   # Create the conda environment
   conda env create --file environment.yml

   # Activate the environment
   conda activate intersect

   # Install the intersect packages using pip in the conda environment, this will
   # ask for your username (UCAMS ID) and password (GitLab token)
   pip install -i https://code.ornl.gov/api/v4/groups/5609/-/packages/pypi/simple intersect-common

After activating the conda environment, run the ``server.py`` in the same terminal session as shown below. The server will begin outputting status messages while measuring its uptime and incrementing a count up from 0 every second.

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

Next, run the ``client.py`` in yet another terminal session. Don't forget to activate the conda environment in this terminal session too. Once run, the client will begin to stop and start the server's count while also requesting its current value.

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

Here.

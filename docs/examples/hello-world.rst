Hello world
===========

This is a basic example to demonstrate how to communicate with the INTERSECT SDK. The ``adapter.py`` subscribes to ``Request`` INTERSECT messages of the ``DETAIL`` subtype. The adapter will respond with a "Hello, World!" message in its reply. The ``requestor.py`` publishes ``Status`` INTERSECT messages of the ``GENERAL`` subtype. See the sections below for running the example using Docker compose or from within a Python environment.

Using Docker compose
--------------------

Here.

Using a Python environment
--------------------------

This section discusses the ``hello-world`` examples in ``examples/python-environment/``. The ``hello-world-dict`` example uses a dictionary for configuration settings while the example in ``hello-world-yml`` uses a YAML configuration file. Follow the steps below to run these examples using a conda environment.

Run the following commands to use the ``environment.yml`` file to create a conda environment for this example:

.. code-block:: bash

   # Create the conda environment
   conda env create --file environment.yml

   # Activate the environment
   conda activate intersect

   # Install the intersect packages using pip in the conda environment, this will
   # ask for your username (UCAMS ID) and password (GitLab token)
   pip install -i https://code.ornl.gov/api/v4/groups/5609/-/packages/pypi/simple intersect-sdk

After starting the broker and activating the conda environment, run the adapter and requestor as follows in separate terminal sessions:

.. code-block:: bash

   # First, run the adapter
   python adapter.py

   # Next, run the requestor in a separate terminal
   python requestor.py

After several seconds, the output from ``adapter.py`` is

.. code-block:: text

   Waiting to connect to broker...
   Press Ctrl-C to exit:
   Adapter Uptime: 6 seconds
   Adapter Uptime: 11 seconds
   Received request from Requestor, sending reply...
   Adapter Uptime: 16 seconds
   Adapter Uptime: 21 seconds

and the output from ``requestor.py`` is

.. code-block:: text

  Waiting to connect to message broker...
  Press Ctrl-C to exit:
  Requestor will send request in 5 seconds...
  Request sent!
  Reply from Hello World Adapter:
  {"message": "Hello, World!"}
  Requestor Uptime: 11 seconds
  Requestor Uptime: 16 seconds
  Requestor Uptime: 21 seconds

Inspecting messages
===================

This example demonstrates how to inspect messages with the INTERSECT SDK. The ``status_publisher.py`` is a simple adapter that only publishes status messages. The ``message_inspector.py`` is an adapter that subscribes to all status messages. See the sections below for running the example using Docker compose or from within a Python environment.

Using a Python environment
--------------------------

This section discusses the ``inspecting-messages`` example in the ``examples/python-environment`` directory. Follow the steps below for running the example in a conda environment.

First, if a broker is not already running, run the broker in a separate terminal session as discussed on the :doc:`../installation` page.

Next, in another terminal session, run the following commands to use the ``environment.yml`` file to create a conda environment for this example:

.. code-block:: bash

   # Create the conda environment
   conda env create --file environment.yml

   # Activate the environment
   conda activate intersect

   # Install the intersect packages using pip in the conda environment, this will
   # ask for your username (UCAMS ID) and password (GitLab token)
   pip install -i https://code.ornl.gov/api/v4/groups/5609/-/packages/pypi/simple intersect-sdk

After activating the conda environment, run the ``status_publisher.py`` in the same terminal session as shown below.

.. code-block:: bash

   python status_publisher.py

The output from ``status_publisher.py`` should look like the following after several seconds:

.. code-block:: text

   Press Ctrl-C to exit:
   Publisher Uptime: 5 seconds
   Publisher Uptime: 10 seconds
   Publisher Uptime: 15 seconds
   Publisher Uptime: 20 seconds
   Publisher Uptime: 25 seconds
   Publisher Uptime: 30 seconds
   Publisher Uptime: 35 seconds

Next, run the ``message_inspector.py`` in yet another terminal session. Don't forget to activate the conda environment in this terminal session too.

.. code-block:: bash

   python message_inspector.py

The output from ``message_inspector.py`` should look like the following after several seconds:

.. code-block:: text

   Waiting to connect to broker...
   header {
     source: "Inspector"
     destination: "None"
     message_id: "Inspector0"
     created: "2023-06-08T20:21:46.355743Z"
   }
   status: STARTING
   detail: "{\"service\": \"Inspector\", \"subsystem\": \"Inspector\", \"system\": \"Inspector\", \"facility\": \"Inspecting Messages Facility\", \"organization\": \"Oak Ridge National Laboratory\", \"capabilities\": [{\"name\": \"Availability_Status\", \"properties\": {\"status\": 4, \"statusDescription\": \"Service Inspector online, starting normal status ticker.\"}}]}"

   header {
     source: "Inspector"
     destination: "None"
     message_id: "Inspector1"
     created: "2023-06-08T20:21:46.356280Z"
   }
   status: STARTING
   detail: "{\"service\": \"Inspector\", \"subsystem\": \"Inspector\", \"system\": \"Inspector\", \"facility\": \"Inspecting Messages Facility\", \"organization\": \"Oak Ridge National Laboratory\", \"capabilities\": [{\"name\": \"Availability_Status\", \"properties\": {\"status\": 4, \"statusDescription\": \"Service Inspector online, starting normal status ticker.\"}}]}"

   header {
     source: "Inspector"
     destination: "None"
     message_id: "Inspector2"
     created: "2023-06-08T20:21:46.356603Z"
   }
   status: AVAILABLE
   detail: "{\"service\": \"Inspector\", \"subsystem\": \"Inspector\", \"system\": \"Inspector\", \"facility\": \"Inspecting Messages Facility\", \"organization\": \"Oak Ridge National Laboratory\"}"

   header {
     source: "Inspector"
     destination: "None"
     message_id: "Inspector0"
     created: "2023-06-08T20:21:46.355743Z"
   }
   status: STARTING
   detail: "{\"service\": \"Inspector\", \"subsystem\": \"Inspector\", \"system\": \"Inspector\", \"facility\": \"Inspecting Messages Facility\", \"organization\": \"Oak Ridge National Laboratory\", \"capabilities\": [{\"name\": \"Availability_Status\", \"properties\": {\"status\": 4, \"statusDescription\": \"Service Inspector online, starting normal status ticker.\"}}]}"

   header {
     source: "Inspector"
     destination: "None"
     message_id: "Inspector1"
     created: "2023-06-08T20:21:46.356280Z"
   }
   status: STARTING
   detail: "{\"service\": \"Inspector\", \"subsystem\": \"Inspector\", \"system\": \"Inspector\", \"facility\": \"Inspecting Messages Facility\", \"organization\": \"Oak Ridge National Laboratory\", \"capabilities\": [{\"name\": \"Availability_Status\", \"properties\": {\"status\": 4, \"statusDescription\": \"Service Inspector online, starting normal status ticker.\"}}]}"

   header {
     source: "Inspector"
     destination: "None"
     message_id: "Inspector2"
     created: "2023-06-08T20:21:46.356603Z"
   }
   status: AVAILABLE
   detail: "{\"service\": \"Inspector\", \"subsystem\": \"Inspector\", \"system\": \"Inspector\", \"facility\": \"Inspecting Messages Facility\", \"organization\": \"Oak Ridge National Laboratory\"}"

   Press Ctrl-C to exit:
   Inspector Uptime: 6 seconds
   Inspector Uptime: 11 seconds
   Inspector Uptime: 16 seconds

Using Docker compose
--------------------

here

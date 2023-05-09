Installation
============

Software, developer tools, and other items that need to be installed for using the Python SDK for INTERSECT are discussed below.

Docker
------

`Docker <https://www.docker.com>`_ is used to create containers for using the Python SDK and to run the examples. Download and install Docker using the instructions provided on their website. See the Authenticating section to use the GitLab Container registry which contains INTERSECT dependencies.

Authenticating
--------------

Some dependencies are stored on private package registries on code.ornl.gov. A personal access token is required in order to install these with either poetry or pip. Create a personal access token on the `Access Tokens page <https://code.ornl.gov/-/profile/personal_access_tokens>`_ in GitLab Preferences with ``read_api`` or ``api`` permissions then save the auto-generated key. This key is only displayed immediately after generating it, so be sure to save it (otherwise a new token will need to be generated).

For the Docker containers, you need to login to the GitLab Container registry using the command shown below. Then sign in with your UCAMS or XCAMS credentials.

.. code-block::

   docker login code.ornl.gov:4567

Broker
------

A broker configuration for SDK developoment is available on the INTERSECT GitLab at https://code.ornl.gov/intersect/sdk/broker. This broker is meant for testing and development purposes and should not be used for deploying INTERSECT in production.

Running the broker
~~~~~~~~~~~~~~~~~~

Run the broker using the following command:

.. code-block::

   docker login code.ornl.gov:4567
   docker run -p 1883:1883 code.ornl.gov:4567/intersect/sdk/broker/0.2.0

To expose the management UI as well, add ``-p 15672:15672`` to the command.
Then you can navigate to localhost:15672 in your browser.
The credentials will be those found in the [broker's definitions.json](https://code.ornl.gov/intersect/sdk/broker/-/blob/0.2.0/definitions.json) to login.

Poetry
------

The `poetry <https://python-poetry.org>`_ packaging and dependency management tool can be used to install the Python SDK. Download and install poetry using the instructions on their website.

Conda
-----

The `conda <https://docs.conda.io/en/latest/>`_ packaging, dependency, and environment management tool can also be used to intall the Python SDK. Install conda from the `Anaconda <https://www.anaconda.com>`_ website or follow the `Conda installation <https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html>`_ steps. Notice that Miniconda is a mini version of Anaconda that includes only conda and its dependencies. If you prefer to have conda plus over 7,500 open-source packages, install Anaconda. Follow the instructions on their website to download and install conda or miniconda.

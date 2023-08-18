Installation
============

Here

Other items that need to be installed for running the examples are discussed below.

Docker
------

`Docker <https://www.docker.com>`_ is used to create containers for using the Python SDK and to run the examples. Download and install Docker using the instructions provided on their website. See the Authenticating section below to use the GitLab Container registry which contains INTERSECT dependencies.

Authenticating
--------------

Some dependencies are stored on private package registries on code.ornl.gov. A personal access token is required in order to install these with either pip or PDM. Create a personal access token on the `Access Tokens page <https://code.ornl.gov/-/profile/personal_access_tokens>`_ in GitLab Preferences with ``read_api`` or ``api`` permissions then save the auto-generated key. This key is only displayed immediately after generating it, so be sure to save it (otherwise a new token will need to be generated).

For the Docker containers, you need to login to the GitLab Container registry using the command shown below. Then sign in with your UCAMS or XCAMS credentials.

.. code-block::

   docker login code.ornl.gov:4567

Broker
------

A broker configuration for SDK developoment is available on the INTERSECT GitLab at https://code.ornl.gov/intersect/sdk/broker. This broker is meant for testing and development purposes and should not be used for deploying INTERSECT in production.

Run the broker using the Docker commands shown below. See the previous section regarding authentication for the login command.

.. code-block::

   docker login code.ornl.gov:4567
   docker run --rm -p 1883:1883 code.ornl.gov:4567/intersect/sdk/broker/0.2.0

To expose the management UI as well, add ``-p 15672:15672`` to the command. Then you can navigate to ``localhost:15672`` in your browser. The login credentials will be those found in the broker's `definitions file <https://code.ornl.gov/intersect/sdk/broker/-/blob/0.2.0/definitions.json>`_.

Conda
-----

`Conda <https://docs.conda.io/en/latest/>`_ is an open-source packaging, dependency, and environment management tool. It can be used to install and implement the INTERSECT Python SDK. Install conda from the `Anaconda <https://www.anaconda.com>`_ website or follow the `Conda installation <https://docs.conda.io/projects/conda/en/stable/user-guide/install/index.html>`_ steps. Notice that Miniconda is a smaller version of Anaconda that includes only conda and its dependencies. Install Anaconda if you prefer to have conda plus over 7,500 open-source packages; otherwise just install Miniconda.

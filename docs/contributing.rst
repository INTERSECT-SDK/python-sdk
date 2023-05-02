Contributing
============

This section discusses documentation, testing, linters, formatters, and style guides for developing the INTERSECT Python SDK.

Environment
-----------

The command shown below uses the ``environment.yml`` file in the python-sdk repository to create a conda environment named ``intersect``. This will install all the dependencies for developing the INTERSECT Python SDK. After running the command, follow the instructions in the terminal to activate the environment.

.. code-block::

   conda env create --file environment.yml

Documentation
-------------

Documentation for the INTERSECT Python SDK is generated with `Sphinx <https://www.sphinx-doc.org/en/master/>`_ from the ``docs`` directory.

Testing
-------

The `pytest <https://docs.pytest.org>`_ framework is used to run tests.

Style guide
-----------

Adhere to the `pep8 <https://pep8.org>`_ style guide for writing Python code.

Linting
-------

Use the `flake8 <https://github.com/PyCQA/flake8>`_ linter tool when writing Python code. Instructions for setting up flake8 with Visual Studio Code are available `here <https://code.visualstudio.com/docs/python/linting>`__. Instructions for setting up flake8 with Sublime Text are available `here <https://lsp.sublimetext.io/>`__ for the LSP-pylsp package.

Formatting
----------

Use the `Black <https://github.com/psf/black>`_ formatter for Python code. Instructions for using this formatter with Visual Studio Code are available `here <https://code.visualstudio.com/docs/python/editing>`__. Instructions for using the formatter with Sublime Text are available `here <https://lsp.sublimetext.io/>`__ for the LSP-pylsp package.

Docstrings
----------

Docstrings for Python classes, functions, and modules should adhere to the `Google style <https://google.github.io/styleguide/pyguide.html>`_. The docstrings are processed by the `napoleon extension <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/>`_ for the Sphinx generated documentation.

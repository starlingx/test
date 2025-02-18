===========
stx-test
===========

StarlingX Test repository for automated test cases.

This repository contains the test framework and test cases for verifying StarlingX. The test framework provides tools for configuration, automation, and execution of tests, with the ability to run against diverse StarlingX lab environments.

Pre-Requisites
--------------

To use this repository, ensure the following requirements are met:

1. **Operating System**:
   - Ubuntu 22.04 or later.

2. **Network Requirements**:
   - The RunAgent (test execution machine) must:
     - Have internet access for pulling images and dependencies.
     - Be able to connect to your StarlingX system(s) via SSH.

3. **Required Tools**:
   Install the following tools:

   .. code-block:: bash

      # Python 3.11
      sudo apt update
      sudo apt install -y python3.11 python3-pip

      # pipenv
      pip install --user pipenv

Setup and Installation
----------------------

1. **Clone the Repository**:

   .. code-block:: bash

      git clone https://opendev.org/starlingx/test.git
      cd test

2. **Setup Gerrit for Code Review**:
   The procedure to set up Gerrit for StarlingX is the same as for other projects hosted on OpenDev, such as OpenStack. Refer to the `OpenStack Contributor Guide <https://docs.openstack.org/contributors/en_GB/common/setup-gerrit.html>`_ for detailed instructions.

   - **Key Setup and Repository Configuration**:

     .. code-block:: bash

        # Generate an SSH key (recommended: ED25519; RSA is also supported)
        ssh-keygen -t ed25519 -C "<your email address>"
        ssh-add ~/.ssh/id_ed25519

        # Alternatively, generate an RSA key for compatibility with older systems:
        ssh-keygen -t rsa -b 4096 -C "<your email address>"
        ssh-add ~/.ssh/id_rsa

     - Add your SSH key to Gerrit:
       - Navigate to https://review.opendev.org/settings/#SSHKeys.
       - Copy the contents of your public key file (`~/.ssh/id_ed25519.pub` or `~/.ssh/id_rsa.pub`).
       - Paste the key into the SSH key field on the Gerrit settings page.

   - **Sign the Individual Contributor License Agreement (ICLA)**:
     Projects hosted on OpenDev, including StarlingX, require signing the `OpenStack Individual Contributor License Agreement (ICLA) <https://docs.openstack.org/contributors/en_GB/common/setup-gerrit.html>`_. This step is outlined in the OpenStack Contributor Guide and the `OpenDev Developer Documentation <https://docs.opendev.org/opendev/infra-manual/latest/developers.html>`_. Follow these instructions to complete the process before submitting changes.

   - **Fetch Gerrit Hooks**:
     Fetch Gerrit hooks immediately after cloning to enable automatic Change-Id generation during commits and verify your SSH key setup:

         .. code-block:: bash

            git review -s

         Example output:

         .. code-block::

            Creating a git remote called 'gerrit' that maps to:
                    ssh://<open-review-email-or-username>@review.opendev.org:29418/starlingx/test.git

         If there is an issue with your SSH configuration (e.g., missing or incorrect SSH key), you will see an error message indicating the problem, such as "Permission denied (publickey)".

     - (Optional) If you cloned the repository using HTTPS or need Gerrit hooks:
       - Add a Gerrit remote (only needed if the default remote does not point to Gerrit).

         .. code-block:: bash

            git remote add gerrit ssh://<your-gerrit-username>@review.opendev.org/starlingx/test.git

3. **Install Python Dependencies**:

   .. code-block:: bash

      # Create and activate a virtual environment
      pipenv shell

      # Sync project dependencies
      pipenv sync

4. **Install Pre-Commit Hooks**:

   .. code-block:: bash

      # Install pre-commit hooks for linting and formatting (run in the repository's root directory)
      pre-commit install

Configuration
-------------

The framework relies on configuration files found under the `config` directory. These include settings for labs, Docker, Kubernetes, and logging. Default files are provided, but you can customize configurations using CLI options.

Steps to Configure
~~~~~~~~~~~~~~~~~~

1. **Lab Configuration (`config/lab/files/default.json5`)**:
   - Holds lab details such as floating IPs, type, and capabilities.
   - For custom setups:
     - Use a template file (e.g., `template_simplex.json5`) as a base.
     - Update `use_jump_host` and `jump_server_config` if a jump server is used.

2. **Docker Configuration (`config/docker/files/default.json5`)**:
   - Specify credentials for Docker registries used during testing.

3. **Lab Capability Scanner**:
   - Automatically detect and update lab capabilities:

     .. code-block:: bash

        python scripts/lab_capability_scanner.py --lab_config_file=<lab_config_file>

You are now ready to execute tests!

Running Tests
-------------

1. **Basic Example**:
   Run a specific test case:

   .. code-block:: bash

      python framework/runner/scripts/test_executor.py --tests_location=<testcase_location>

2. **Custom Configurations**:
   Use non-default configurations:

   .. code-block:: bash

      python framework/runner/scripts/test_executor.py \
        --tests_location=<testcase_location> \
        --lab_config_file=<config_location>

   Example:

   .. code-block:: bash

      python framework/runner/scripts/test_executor.py \
        --tests_location=testcases/cloud_platform/sanity \
        --lab_config_file=config/lab/files/custom_config.json5

3. **UI Testing (Optional)**:
   Install Chrome for running WebDriver-based UI tests:

   .. code-block:: bash

      wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
      sudo dpkg -i google-chrome-stable_current_amd64.deb
      sudo apt -f install
      google-chrome --version

Contribution
------------

2. **Coding Standards**:
   - Ensure your code adheres to project conventions. For detailed guidelines, see `CONTRIBUTING.rst`.
   - Pre-commit hooks will run automatically on every commit once installed to ensure formatting and linting.

   - **Tools Enforced by Pre-Commit Hooks**:
     - `pre-commit <https://pre-commit.com/>`_
     - `black <https://black.readthedocs.io/en/stable/>`_
     - `isort <https://pycqa.github.io/isort/>`_
     - `flake8 <https://flake8.pycqa.org/en/latest/>`_
     - `pydocstyle <https://www.pydocstyle.org/en/latest/>`_
     - `pydoclint <https://github.com/jsh9/pydoclint>`_
     - `interrogate <https://interrogate.readthedocs.io/en/latest/>`_

3. **Submitting Changes**:
   - Ensure your commit messages adhere to the guidelines in the
     `OpenStack Git Commit Message Guidelines <https://wiki.openstack.org/wiki/GitCommitMessages>`_.
   - Submit changes for Gerrit review using the following example:

     .. code-block:: bash

        git commit -s # include sign-off
        git review

6. References
=============

- `OpenStack Contributor Guide <https://docs.openstack.org/contributors/en_GB/common/setup-gerrit.html>`_
- `OpenStack Individual Contributor License Agreement (ICLA) <https://review.opendev.org/settings/new-agreement>`_
- `OpenDev Developer Documentation <https://docs.opendev.org/opendev/infra-manual/latest/developers.html>`_
- `StarlingX Contributor Guidelines <https://docs.starlingx.io/contributor/index.html>`_
- `StarlingX Code Submission Guide <https://docs.starlingx.io/developer_resources/code-submission-guide.html>`_
- `How to Contribute to StarlingX (YouTube) <https://www.youtube.com/watch?v=oHmx0M3cYlE>`_
- `OpenStack Git Commit Message Guidelines <https://wiki.openstack.org/wiki/GitCommitMessages>`_
- `Google Python Style Guide <https://google.github.io/styleguide/pyguide.html#381-docstrings>`_
- `PEP 257 (Docstring Conventions) <https://peps.python.org/pep-0257/>`_
- `PEP 484 (Type Hints) <https://peps.python.org/pep-0484/>`_
- `PEP 498 (f-Strings) <https://peps.python.org/pep-0498/>`_
- `pydocstyle Documentation <https://www.pydocstyle.org/en/latest/>`_
- `pydoclint Documentation <https://github.com/jsh9/pydoclint>`_
- `interrogate Documentation <https://interrogate.readthedocs.io/en/latest/>`_
- `pre-commit <https://pre-commit.com/>`_
- `black <https://black.readthedocs.io/en/stable/>`_
- `isort <https://pycqa.github.io/isort/>`_
- `flake8 <https://flake8.pycqa.org/en/latest/>`_
- `AutoDocstring for VSCode <https://github.com/autosoft-dev/autoDocstring>`_
- `VSCode: Auto-Generating Docstrings <https://code.visualstudio.com/docs/python/editing#_auto-generating-docstrings>`_
- `PyCharm: Creating Documentation Comments <https://www.jetbrains.com/help/pycharm/creating-documentation-comments.html>`_

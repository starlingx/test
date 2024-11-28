========
stx-test
========

StarlingX Test repository for automated test cases.

Pre-Requisites
----------

.. code-block:: bash

    You must have a machine/VM running Ubuntu 22.04 or later
    The RunAgent must be able to connect to the internet to pull images and dependencies.
    The RunAgent must be able to connect to your labs via SSH.
    Download and install Python 3.11, pip and pipenv.
    Download and install git on the RunAgent

Contribute
----------

- Clone the repo
- Gerrit hook needs to be added for code review purpose.

.. code-block:: bash

    # Generate a ssh key if needed
    ssh-keygen -t rsa -C "<your email address>"
    ssh-add $private_keyfile_path

    # Add ssh key to settings https://review.opendev.org/#/q/project:starlingx/test
    cd <stx-test repo>
    git remote add gerrit ssh://<your gerrit username>@review.opendev.org/starlingx/test.git
    git review -s

    # Create/activate a virtual python environment and pull the project dependencies.
    pipenv shell
    pipenv sync

- When you are ready, create your commit with detailed commit message, and submit for review.

Configuration
----------

The framework contains multiple configuration files found under the config folder. There are configurations for docker,
hosts, kubernetes, labs and logger. By default, the runner will choose the default config file for each (default.json5)
when running. These files can be found under config/<config_type>/files. However, using command line overrides a user
can use a custom file. Command line options are --lab_config_file, --k8s_config_file, --logger_config_file, and --docker_config_file.

There are a couple of files that will need to be updated when first setting up.

1) config/lab/files/default.json5

This file is responsible for holding information such as floating ip, lab type, lab capabilities etc. Adjust the
contents of default.json5 to match the information of the lab where you want to execute the test cases. Based on your
system type, you can use one of the template files (such as template_simplex.json5) as a starting point. If using a
jump server, update the values under config/host/files/jump_host.json5 to use the connection information of the
jump server. Then in the lab configuration file, set "use_jump_host: true", and the "jump_server_config:<jump_host_location>"
(ex. jump_server_config: "config/host/files/jump_host.json5")

2) config/docker/files/default.json5

This file is responsible for holding information for docker registries used in testing. Adjust the local registry
credentials to match those of the lab where you want to execute the tests.

Update Lab Capabilities
Using the lab capability scanner, we can identify common lab capabilities and automatically add them to the configuration.
This script will create a backup of the original file and create a new one with the lab capabilities added. These
capabilities will help identify which tests are applicable for a given lab setup.

// Run script from the root location of the repo
cd <repo_location_root>
python scripts/lab_capability_scanner.py --lab_config_file=<lab_config_file>


.. code-block:: bash

    # (Optional) Install Chrome for Webdriver UI tests
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo dpkg -i google-chrome-stable_current_amd64.deb
    sudo apt -f install            [If you encounter errors during the install]
    google-chrome --version        [Verify that the install was successful]

Execution
----------

You are now ready to run some tests!

// From the root repo location we can now run tests
cd <repo_location_root>
python framework/runner/scripts/test_executor.py --tests_location=<testcase_location>

// Note non-default config locations and filenames are also supported on the commandline as --lab_config_file, --k8s_config_file, --logger_config_file, --docker_config_file
python framework/runner/scripts/test_executor.py --tests_location=<testcase_location> --lab_config_file=<config_location>

// Ex. python framework/runner/scripts/test_executor.py --tests_location=testcases/cloud_platform/sanity --lab_config_file=/dev/configs/my_config.json

====================================
StarlingX Integration Test Framework
====================================

The project contains integration test cases that can be executed on an
installed and configured StarlingX system.

Supported test cases:

- CLI tests over SSH connection to StarlingX system via OAM floating IP
- Platform RestAPI test cases via external endpoints
- Horizon test cases


Packages Required
-----------------
- python >='3.4.3,<3.7'
- pytest>='3.1.0,<4.0'
- pexpect
- pyyaml
- requests  (used by RestAPI test cases only)
- selenium  (used by Horizon test cases only)
- Firefox (used by Horizon test cases only)
- pyvirtualdisplay  (used by Horizon test cases only)
- ffmpeg    (used by Horizon test cases only)
- Xvfb or Xephyr or Xvnc  (used by pyvirtualdisplay for Horizon test cases only)


Setup Test Tool
---------------
This is a off-box test tool that needs to be set up once on a Linux server
that can reach the StarlingX system under test (such as SSH to STX
system, send/receive RestAPI requests, open Horizon page).

- Install above packages
- Clone stx-test repo
- Add absolute path for automated-pytest-suite to PYTHONPATH environment variable

Execute Test Cases
------------------
Precondition: STX system under test should be installed and configured.

- | Customized config can be provided via --testcase-config <config_file>.
  | Config template can be found at ${project_root}/stx-test_template.conf.
- Test cases can be selected by specifying via -m <markers>
- | If stx-openstack is not deployed, platform specific marker should be specified,
  | e.g., -m "platform_sanity or platform"
- | Automation logs will be created at ${HOME}/AUTOMATION_LOGS directory by default.
  | Log directory can also be specified with --resultlog=${LOG_DIR} commandline option
- Examples:

.. code-block:: bash

    export project_root=<automated-pytest-suite dir>

    # Include $project_root to PYTHONPATH if not already done
    export PYTHONPATH=${PYTHONPATH}:${project_root}

    cd $project_root

    # Example 1: Run all platform_sanity test cases under testcases/
    pytest -m platform_sanity --testcase-config=~/my_config.conf testcases/

    # Example 2: Run platform_sanity or sanity (requires stx-openstack) test cases,
    # on a StarlingX virtual box system that is already saved in consts/lab.py
    # and save automation logs to /tmp/AUTOMATION_LOGS
    pytest --resultlog=/tmp/ -m sanity --lab=vbox --natbox=localhost testcases/

    # Example 3: List (not execute) the test cases with "migrate" in the name
    pytest --collect-only -k "migrate" --lab=<stx_oam_fip> testcases/


Contribute
----------

- In order to contribute, python3.4 is required to avoid producing code that is incompatible with python3.4.

"""Analytics (wr-analytics) Setup Test.

Deploys the wr-analytics application with the system test helm overrides,
from the tarball the lab install leaves in the home directory.

For DC systems, deploys on the System Controller (Central Cloud) first with
metricbeat overrides, then on the subcloud with security and metricbeat
overrides. For standalone systems, deploys only on the active controller.

Prerequisites:
- Lab is accessible
- The WRA tarball is at /home/sysadmin/wr-analytics.tgz on every system that
  gets WRA (the lab install places it there)
- For DC systems: lab config has system_controller_ip defined and the system
  controller is reachable

Run with:
    pytest testcases/cloud_platform/system_test/test_setup_wra.py \
        --lab_config_file=config/lab/files/<lab>.json5
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.system_test.setup_wra_keywords import SetupWraKeywords


@mark.p1
def test_setup_wra() -> None:
    """Deploy WRA with the system test overrides on a DC or standalone system.

    Test Steps:
        - If DC: deploy WRA on the system controller, then on the subcloud
        - If standalone: deploy WRA on the active controller
    """
    lab_config = ConfigurationManager.get_lab_config()
    system_controller_ip = lab_config.get_system_controller_ip()

    if not system_controller_ip:
        get_logger().log_test_case_step("Deploy WRA on standalone system")
        ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        SetupWraKeywords(sc_ssh=ssh_connection).deploy_wra_standalone()
        return

    ssh_user = lab_config.get_admin_credentials().get_user_name()
    ssh_password = lab_config.get_admin_credentials().get_password()

    jump_host_config = None
    if lab_config.is_use_jump_server():
        jump_host_config = lab_config.get_jump_host_configuration()

    get_logger().log_setup_step("Connecting to system controller")
    sc_ssh = SSHConnectionManager.create_ssh_connection(
        system_controller_ip,
        ssh_user,
        ssh_password,
        ssh_port=lab_config.get_ssh_port(),
        jump_host=jump_host_config,
    )

    get_logger().log_setup_step("Connecting to subcloud")
    subcloud_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Deploy WRA on system controller and subcloud")
    wra_keywords = SetupWraKeywords(
        sc_ssh=sc_ssh,
        subcloud_ssh=subcloud_ssh,
        system_controller_ip=system_controller_ip,
        ssh_user=ssh_user,
        ssh_password=ssh_password,
    )
    wra_keywords.deploy_wra_dc()

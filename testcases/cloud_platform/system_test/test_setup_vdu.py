"""VDU (Virtual Deployment Unit) Setup Test.

Downloads VDU test data and runs the install script to deploy
images, apps, and VDU workloads on the lab.

For DC systems, deploys on the system controller first (always fail_ok=True),
then on the subcloud (uses fail_ok from config).
For standalone systems, deploys only on the active controller.

Prerequisites:
- Lab is accessible
- VDU server config (config/system_test/files/default_vdu.json5) is populated
- The remote server has the test-data folder with install_all.sh

Run with:
    pytest testcases/cloud_platform/system_test/test_setup_vdu.py \
        --lab_config_file=config/lab/files/<lab>.json5
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.system_test.setup_vdu_keywords import SetupVduKeywords


@mark.p1
def test_setup_vdu() -> None:
    """Download VDU test data and run install script.

    Test Steps:
        - If DC: Deploy VDU on system controller and subcloud
    """
    lab_config = ConfigurationManager.get_lab_config()
    system_controller_ip = lab_config.get_system_controller_ip()
    
    if system_controller_ip:
        # DC system — deploy on system controller first (always allow failures)
        ssh_user = lab_config.get_admin_credentials().get_user_name()
        ssh_password = lab_config.get_admin_credentials().get_password()

        jump_host_config = None
        if lab_config.is_use_jump_server():
            jump_host_config = lab_config.get_jump_host_configuration()

        get_logger().log_test_case_step("Deploy VDU on system controller")
        sc_ssh = SSHConnectionManager.create_ssh_connection(
            system_controller_ip,
            ssh_user,
            ssh_password,
            ssh_port=lab_config.get_ssh_port(),
            jump_host=jump_host_config,
        )
        SetupVduKeywords(sc_ssh).deploy_vdu(fail_ok_override=True, stx_apps_only=True)

    get_logger().log_test_case_step("Deploy VDU on host")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    SetupVduKeywords(ssh_connection).deploy_vdu()

    get_logger().log_info("VDU setup completed")

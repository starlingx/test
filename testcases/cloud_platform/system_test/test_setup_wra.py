"""WRA (Wind River Analytics) DC Deployment Test.

Deploys the wr-analytics application on a Distributed Cloud (DC) system.
Downloads the WRA tarball from an external build server, deploys on the
System Controller (Central Cloud) first with metricbeat overrides, then
deploys to the subcloud with security and metricbeat overrides.

Prerequisites:
- System is a Distributed Cloud (DC)
- Lab config has system_controller_ip defined
- WRA tarball is available on the configured build server
- The subcloud (floating_ip) and system controller are reachable
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection_manager import SSHConnectionManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.system_test.setup_wra_keywords import SetupWraKeywords


@mark.p1
def test_setup_wra_dc() -> None:
    """Deploy WRA on a DC system (system controller + subcloud).

    Downloads the WRA tarball from the build server, deploys on the system
    controller with metricbeat overrides, then deploys on the subcloud with
    both metricbeat and security overrides.

    Test Steps:
        1. Download WRA tarball to system controller
        2. Remove existing WRA if present on system controller
        3. Assign WRA labels on system controller hosts
        4. Upload WRA on system controller
        5. Create and apply metricbeat overrides on system controller
        6. Apply WRA on system controller
        7. Verify WRA pods healthy on system controller
        8. Download WRA tarball to subcloud
        9. Remove existing WRA if present on subcloud
        10. Assign WRA labels on subcloud
        11. Upload WRA on subcloud
        12. Create and apply metricbeat overrides on subcloud
        13. Copy security overrides from system controller to subcloud
        14. Apply security overrides on subcloud
        15. Apply WRA on subcloud
        16. Verify WRA pods healthy on subcloud
    """
    # --- Setup: Get connections ---
    lab_config = ConfigurationManager.get_lab_config()
    system_controller_ip = lab_config.get_system_controller_ip()
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

    # --- Execute WRA deployment ---
    wra_keywords = SetupWraKeywords(
        sc_ssh=sc_ssh,
        subcloud_ssh=subcloud_ssh,
        system_controller_ip=system_controller_ip,
        ssh_user=ssh_user,
        ssh_password=ssh_password,
    )
    wra_keywords.deploy_wra_dc()

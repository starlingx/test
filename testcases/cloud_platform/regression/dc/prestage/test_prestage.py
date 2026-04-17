import re

from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_prestage_strategy_keywords import DcmanagerPrestageStrategyKeywords
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.linux.pkill.pkill_keywords import PkillKeywords


def subcloud_upgrade(central_ssh, subcloud_name):
    """Upgrade subcloud"""
    # delete existing prestage strategy
    DcmanagerPrestageStrategyKeywords(central_ssh).get_dcmanager_prestage_strategy_delete()
    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    sw_release = SoftwareListKeywords(central_ssh).get_software_list().get_release_name_by_state("deployed")
    latest_deployed_release = max(sw_release)
    # Create software deploy strategy
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, release=latest_deployed_release, with_delete=True)

    # Apply the previously created strategy
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(target=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")


def prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy: bool = False, expect_fail: bool = False):
    """Prestage subcloud"""

    get_logger().log_info(f"Subcloud selected for prestage: {subcloud_name}")
    wait_completion = not expect_fail
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name, subcloud_password, for_sw_deploy=for_sw_deploy, wait_completion=wait_completion)

    # validate prestage status
    if expect_fail:
        # kill prestage playbook
        prestage_playbook = "/usr/share/ansible/stx-ansible/playbooks/prestage_sw_packages.yml"
        PkillKeywords(central_ssh).pkill_by_pattern(prestage_playbook, send_as_sudo=True)
        prestage_result = "failed"
        success_msg = f"subcloud {subcloud_name} prestage failed."
    else:
        prestage_result = "complete"
        success_msg = f"subcloud {subcloud_name} prestage success."

    obj_subcloud = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name)
    validate_equals(obj_subcloud.get_prestage_status(), prestage_result, success_msg)


@mark.p0
@mark.lab_has_subcloud
def test_subcloud_prestage():
    """Test the prestage of a subcloud."""
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    sc_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(sc_name)
    SystemHostSwactKeywords(subcloud_ssh).ensure_duplex_subcloud_c0_is_active(sc_name)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

    # Gets the lowest subcloud sysadmin password
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(sc_name)
    syspass = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(ssh_connection, sc_name, syspass)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.lab_has_subcloud
def test_major_release_prestage_retry_after_fail():
    """Verify major release prestage retry after fail and do subcloud upgrade

    Test Steps:
        - Verify subcloud health
        - Prestage subcloud
        - Kill prestage playbook to make prestage fail
        - Retry prestage
        - Upgrade subcloud after prestage complete
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    last_major_release = CloudPlatformVersionManagerClass().get_last_major_release()
    get_logger().log_info(f"Subcloud release {last_major_release}")

    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    if subcloud_sw_version != last_major_release:
        fail(f"{subcloud_name} in running {subcloud_sw_version} version, should be {last_major_release}.")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for prestage, backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, expect_fail=True)

    # Retry prestage subcloud
    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)

    subcloud_upgrade(central_ssh, subcloud_name)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()


@mark.p0
@mark.lab_has_subcloud
def test_minor_release_prestage_retry_after_fail():
    """Verify minor release prestage retry after fail and do subcloud upgrade

    Test Steps:
        - Verify subcloud health
        - Prestage subcloud
        - Kill prestage playbook to make prestage fail
        - Retry prestage
        - Upgrade subcloud after prestage complete
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    latest_deployed_release_with_patch = max(SoftwareListKeywords(central_ssh).get_software_list().get_product_version_with_patch_by_state("deployed"))
    latest_deployed_release = max(SoftwareListKeywords(central_ssh).get_software_list().get_product_version_by_state("deployed"))
    get_logger().log_info(f"Subcloud release {latest_deployed_release_with_patch}")

    # Verify that controller has a patch to apply
    patch = re.findall(r"(\.\d+)", latest_deployed_release_with_patch)[1]

    if not patch or patch == ".0":
        fail(f"Controller is running major version {latest_deployed_release}, not minor.")
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    if subcloud_sw_version != latest_deployed_release:
        fail(f"{subcloud_name} is running {subcloud_sw_version} version, should be {latest_deployed_release}.")

    # Prechecks Before Prestage
    get_logger().log_info(f"Performing pre-checks on {subcloud_name}")
    obj_health = HealthKeywords(subcloud_ssh)
    obj_health.validate_healty_cluster()  # Checks alarms, pods, app health

    # Gets the lowest subcloud sysadmin password needed for prestage, backup creation and deletion on central_path.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True, expect_fail=True)

    # Retry prestage subcloud
    prestage_subcloud(central_ssh, subcloud_name, subcloud_password, for_sw_deploy=True)

    subcloud_upgrade(central_ssh, subcloud_name)

    # validate Healthy status
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

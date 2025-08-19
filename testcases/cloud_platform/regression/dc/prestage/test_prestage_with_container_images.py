from pytest import mark

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
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p0
@mark.lab_has_subcloud
def test_subcloud_prestage_with_images():
    """Test the prestage of a subcloud."""
    # Gets the SSH connection to the active controller of the central cloud.
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_lower_id_async_subcloud()
    subcloud_name = lowest_subcloud.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Gets the lowest subcloud sysadmin password
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    syspass = lab_config.get_admin_credentials().get_password()
    subcloud_sw_version = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    sw_release = SoftwareListKeywords(central_ssh).get_software_list().get_release_name_by_state("deployed")
    latest_deployed_release = max(sw_release)

    # Attempt sw-deploy-strategy and prestage-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()
    DcmanagerPrestageStrategyKeywords(central_ssh).get_dcmanager_prestage_strategy_delete()

    remote_registry_path = f"/opt/platform-backup/{subcloud_sw_version}"

    # Create prestage strategy for subcloud
    DcmanagerPrestageStrategyKeywords(central_ssh).get_dcmanager_prestage_strategy_create(sw_deploy=False, subcloud_name=subcloud_name)

    # Apply strategy to subcloud
    DcmanagerPrestageStrategyKeywords(central_ssh).get_dcmanager_prestage_strategy_apply()

    get_logger().log_info("Checking if local registry file is created...")
    FileKeywords(subcloud_ssh).file_exists(f"{remote_registry_path}/local_registry_filesystem.tgz")

    # Remove prestage strategy
    DcmanagerPrestageStrategyKeywords(central_ssh).get_dcmanager_prestage_strategy_delete()

    # Prestage the subcloud with the latest software deployed in the controller
    get_logger().log_info(f"Prestage {subcloud_name} with {sw_release}.")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name=subcloud_name, syspass=syspass, for_sw_deploy=True)

    # Create software deploy strategy
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, sw_version=latest_deployed_release, with_delete=True)

    # Apply the previously created strategy
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(subcloud_name=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")

    # validate Healthy status
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

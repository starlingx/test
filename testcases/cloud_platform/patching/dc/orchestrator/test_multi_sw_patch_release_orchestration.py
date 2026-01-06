from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_strategy_step_keywords import DcmanagerStrategyStepKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.dcmanager.dcmanager_sw_deploy_strategy_keywords import DcmanagerSwDeployStrategy
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords


@mark.p2
@mark.lab_has_subcloud
def test_patch_apply(request):
    """
    Verify patch application on subcloud

    Test Steps:
        - Prestage the subcloud with 25.09.1
        - Create the sw deploy strategy for 25.09.1
        - Apply strategy steps to subcloud

    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(central_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_lower_id_async_subcloud()

    subcloud_name = lowest_subcloud.get_name()

    # Gets the lowest subcloud sysadmin password needed for backup creation.
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    sw_release = SoftwareListKeywords(central_ssh).get_software_list().get_release_name_by_state("deployed")

    # First sw release to be deployed
    first_deploy_release = sw_release[-2]

    # Second sw release to be deployed
    last_deploy_release = sw_release[-1]

    if len(sw_release) <= 2:
        fail("Less than two releases in system controller, lab must have more than two releases deployed.")

    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    # Prestage the subcloud with the latest software deployed in the controller
    get_logger().log_info(f"Prestage {subcloud_name} with {first_deploy_release}.")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name=subcloud_name, syspass=subcloud_password, for_sw_deploy=True)

    # Create first software deploy strategy
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, sw_version=first_deploy_release)

    # Apply the previously created strategy
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(subcloud_name=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")

    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    # Attempt sw-deploy-strategy delete to prevent sw-deploy-strategy create failure.
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_delete()

    # Prestage the subcloud with the latest software deployed in the controller
    get_logger().log_info(f"Prestage {subcloud_name} with {last_deploy_release}.")
    DcmanagerSubcloudPrestage(central_ssh).dcmanager_subcloud_prestage(subcloud_name=subcloud_name, syspass=subcloud_password, for_sw_deploy=True)

    # Create second software deploy strategy
    get_logger().log_info(f"Create sw-deploy strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_create(subcloud_name=subcloud_name, sw_version=last_deploy_release)

    # Apply the second strategy created
    get_logger().log_info(f"Apply strategy for {subcloud_name}.")
    DcmanagerSwDeployStrategy(central_ssh).dcmanager_sw_deploy_strategy_apply(subcloud_name=subcloud_name)

    strategy_status = DcmanagerStrategyStepKeywords(central_ssh).get_dcmanager_strategy_step_show(subcloud_name).get_dcmanager_strategy_step_show().get_state()

    # Verify that the strategy was applied correctly
    validate_equals(strategy_status, "complete", f"Software deploy completed successfully for subcloud {subcloud_name}.")

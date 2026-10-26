from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_not_equals_with_retry
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_management_enum import DcManagerSubcloudListManagementEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p2
@mark.lab_has_subcloud
def test_reconfig_one_subcloud(request):
    """
    Execute a subcloud reconfiguration

    Test Steps:
        - Increase the docker filesystem size by 1 GiB in the deployment config.
        - Run dcmanager subcloud deploy config command.
        - Verify that the docker storage size increased.
    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()

    # Gets the lowest-id healthy subcloud that is also declared in the lab config, together
    # with the SSH connection of the system controller that owns it, so the reconfiguration
    # is driven from the peer cloud when the subcloud has been rehomed to it.
    system_controller_ssh, subcloud_pick = SubcloudPickerKeywords.pick_with_fallback(management_status=DcManagerSubcloudListManagementEnum.MANAGED, availability=DcManagerSubcloudListAvailabilityEnum.ONLINE, in_sync=True)
    subcloud_name = subcloud_pick.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # The profile to edit and the filesystem to measure both belong to the subcloud.
    hostname = SystemHostListKeywords(subcloud_ssh).get_active_controller().get_host_name()

    deployment_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()

    get_logger().log_info(f"Creating backup for {deployment_file}")
    FileKeywords(system_controller_ssh).copy_file(deployment_file, f"{deployment_file}.backup")

    def teardown():
        get_logger().log_teardown_step("Restore deployment config file data.")
        FileKeywords(system_controller_ssh).move_file(f"{deployment_file}.backup", deployment_file)

    request.addfinalizer(teardown)

    system_host_fs_keywords = SystemHostFSKeywords(subcloud_ssh)
    old_fs_size = system_host_fs_keywords.get_system_host_fs_list(host_name=hostname).get_system_host_fs("docker").get_size()

    get_logger().log_test_case_step(f"Increasing docker filesystem size to {old_fs_size + 1} GiB in the deployment config.")
    HostProfileYamlKeywords(system_controller_ssh).edit_yaml_spec_storage(searched_metadata=f"{hostname}-profile", fs="docker", size=old_fs_size + 1, remote_filename=deployment_file)

    get_logger().log_test_case_step(f"Running deploy config for {subcloud_name}.")
    DCManagerSubcloudDeployKeywords(system_controller_ssh).dcmanager_subcloud_deploy_config(subcloud_name=subcloud_name)

    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_availability_status(subcloud_name)

    # The filesystem is resized after the deploy config command returns.
    get_logger().log_test_case_step("Verifying the docker filesystem size increased.")
    validate_not_equals_with_retry(
        function_to_execute=lambda: system_host_fs_keywords.get_system_host_fs_list(host_name=hostname).get_system_host_fs("docker").get_size(),
        not_expected_value=old_fs_size,
        validation_description="Validate that filesystem size for docker changed.",
        timeout=600,
        polling_sleep_time=30,
    )

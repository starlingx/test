from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.validation.validation import validate_not_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_deploy_keywords import DCManagerSubcloudDeployKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_object import DcManagerSubcloudDeployObject
from keywords.cloud_platform.deployment_assets.host_profile_yaml_keywords import HostProfileYamlKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_fs_keywords import SystemHostFSKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords


@mark.p2
@mark.lab_has_subcloud
def test_reconfig_one_subcloud(request):
    """
    Execute a subcloud reconfiguration

    Test Steps:
        - Modify docker size from 30 to 32.
        - Run dcmanager subcloud deploy config command.
        - Verify that the docker storage size increased from 30 to 32.
    """

    deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(system_controller_ssh)
    lowest_subcloud = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    subcloud_name = lowest_subcloud.get_name()

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    deployment_file = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name).get_deployment_config_file()
    hostname = SystemHostListKeywords(system_controller_ssh).get_active_controller().get_host_name()

    HostProfileYamlKeywords(system_controller_ssh).edit_yaml_spec_storage(searched_metadata=f"{hostname}-profile", fs="docker", size=48, remote_filename=deployment_file)
    old_fs_size = SystemHostFSKeywords(subcloud_ssh).get_system_host_fs_list(host_name=hostname).get_system_host_fs("docker").get_size()

    DCManagerSubcloudDeployKeywords(system_controller_ssh).dcmanager_subcloud_deploy_config(subcloud_name=subcloud_name)

    new_fs_size = SystemHostFSKeywords(subcloud_ssh).get_system_host_fs_list(host_name=hostname).get_system_host_fs("docker").get_size()

    dcmanager_subcloud_list_keywords.validate_subcloud_availability_status(subcloud_name)
    validate_not_equals(old_fs_size, new_fs_size, "Validate that filesystem size for docker changed.")

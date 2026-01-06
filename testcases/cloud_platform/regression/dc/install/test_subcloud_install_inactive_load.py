from pytest import fail, mark

from keywords.cloud_platform.dcmanager.dcmanager_subcloud_add_keywords import DcManagerSubcloudAddKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManagerClass
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords


@mark.p2
@mark.lab_has_subcloud
def test_subcloud_install_inactive_load(request):
    """
    Execute a subcloud install with an inactive load.

    Test Steps:
        - Ensure central cloud has 25.09 as active load, and 24.09
          as inactive load and available.
        - Run dcmanager subcloud add using parameter --release,
          passing version 24.09 to it.

    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    inactive_load = CloudPlatformVersionManagerClass().get_last_major_release()

    dcm_sc_list_kw = DcManagerSubcloudListKeywords(system_controller_ssh)
    subcloud_name = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_undeployed_subcloud_name()
    sw_list = SoftwareListKeywords(system_controller_ssh).get_software_list().get_software_lists()
    release_list = [x.release for x in sw_list]

    if inactive_load not in release_list:
        fail("Defined N-1 software not available.")

    DcManagerSubcloudAddKeywords(system_controller_ssh).dcmanager_subcloud_add(subcloud_name=subcloud_name, release_id=str(inactive_load))

    DcManagerSubcloudListKeywords(system_controller_ssh).validate_subcloud_availability_status(subcloud_name)

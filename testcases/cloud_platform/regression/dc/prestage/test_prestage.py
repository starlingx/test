from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_prestage import DcmanagerSubcloudPrestage
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p0
@mark.lab_has_subcloud
def test_subcloud_prestage():
    """Test the prestage of a subcloud."""
    # Gets the SSH connection to the active controller of the central cloud.
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    # Gets the lowest subcloud (the subcloud with the lowest id).
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    lowest_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    sc_name = lowest_subcloud.get_name()
    # Gets the lowest subcloud sysadmin password
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(sc_name)
    syspass = lab_config.get_admin_credentials().get_password()

    get_logger().log_info(f"Subcloud selected for prestage: {sc_name}")
    DcmanagerSubcloudPrestage(ssh_connection).dcmanager_subcloud_prestage(sc_name, syspass)
    # validate prestage status
    obj_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(sc_name)
    # Verify that the prestage is completed successfully
    validate_equals(obj_subcloud.get_prestage_status(), "complete", f"subcloud {sc_name} successfully.")

    # validate Healthy status
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(sc_name)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

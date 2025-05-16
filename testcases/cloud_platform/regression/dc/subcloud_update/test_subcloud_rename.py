import time

from pytest import mark

from framework.kpi.time_kpi import TimeKPI
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_update_keywords import DcManagerSubcloudUpdateKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p0
@mark.lab_has_subcloud
def test_dc_subcloud_rename(request):
    """
    Verify subcloud rename

    Test Steps:
        - log onto active controller
        - Get original name
        - Run dcmanager subcloud update <subcloud_name> --name <new_name>
        - validate that subcloud has new name
        - log the time kpi takes from out-of-sync to in-sync
        - Reset name back to old name
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    # new name used for renaming
    sc_name_new = "testsubcloudrename"
    # Get the lowest subcloud (the subcloud with the lowest id).
    dcm_sc_list_kw = DcManagerSubcloudListKeywords(ssh_connection)
    lowest_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_healthy_subcloud_with_lowest_id()
    sc_name_original = lowest_subcloud.get_name()
    get_logger().log_info(f"Subcloud selected for rename: {sc_name_original}")

    # unmange before rename
    dcm_sc_kw = DcManagerSubcloudManagerKeywords(ssh_connection)
    dcm_sc_manage_out = dcm_sc_kw.get_dcmanager_subcloud_unmanage(sc_name_original, 300)
    get_logger().log_info(f"The management state of the subcloud {sc_name_original} was changed to {dcm_sc_manage_out.get_dcmanager_subcloud_manage_object().get_management()}.")

    time_kpi = TimeKPI(time.time())
    subcloud_update_output = DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(sc_name_original, "name", sc_name_new)
    get_logger().log_info(f"sc rename: {subcloud_update_output.get_dcmanager_subcloud_show_object().__dict__}")
    dcm_sc_manage_out = dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_new, 300)

    def teardown():
        dcm_sc_kw.get_dcmanager_subcloud_unmanage(sc_name_new, 300)
        DcManagerSubcloudUpdateKeywords(ssh_connection).dcmanager_subcloud_update(sc_name_new, "name", sc_name_original)
        # manage the cloud back
        dcm_sc_kw.get_dcmanager_subcloud_manage(sc_name_original, 300)

    # Register the teardown function to be called after the test
    request.addfinalizer(teardown)

    obj_subcloud = dcm_sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(sc_name_new)
    validate_equals(obj_subcloud.get_name(), sc_name_new, "Validate that the name has been changed")
    # Validate that subcloud is in Insync Status
    dcm_sc_list_kw.validate_subcloud_sync_status(sc_name_new, "in-sync")
    time_kpi.log_elapsed_time(time.time(), "time taken for subcloud In-Sync")
    # validate Healthy status
    # since the lab_config does not have the renamed subcloud name, using the original name to ssh
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(sc_name_original)
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

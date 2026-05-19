from typing import List

from pytest import fail, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_manager_keywords import DcManagerSubcloudManagerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

@mark.p2
@mark.lab_has_subcloud
def test_subcloud_management():
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Gets the lowest subcloud (the subcloud with the lowest id).
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    def get_mgmt():
        return DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_management()

    def get_sync_status():
        return DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud_name).get_sync()

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_unmanage(subcloud_name, 10)
    validate_equals_with_retry(get_mgmt, "unmanaged", "Validates that subcloud is unmanaged")
    validate_equals_with_retry(get_sync_status, "out-of-sync", "Validate subcloud is out-of-sync.")

    DcManagerSubcloudManagerKeywords(central_ssh).get_dcmanager_subcloud_manage(subcloud_name, 10)
    validate_equals_with_retry(get_mgmt, "managed", "Validates that subcloud is managed.")
    validate_equals_with_retry(get_sync_status, "in-sync", "Validate subcloud is in-sync.")

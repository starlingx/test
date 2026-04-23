import time

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.kpi.time_kpi import TimeKPI
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.backup_restore.backup_files_upload_keywords import BackUpFilesUploadKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.sw_patch.software_patch_keywords import SwPatchQueryKeywords
from keywords.cloud_platform.upgrade.software_list_keywords import SoftwareListKeywords
from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.files.file_keywords import FileKeywords


@mark.p0
def test_backup():
    """
    Test system backup using ansible playbook

    Test Steps:
      - Take a system backup
      - Verify backup is successful
      - copy to local test server

    """
    lab_type = ConfigurationManager.get_lab_config().get_lab_type()
    backup_dir = "/opt/backups"
    bnr_base_path = ConfigurationManager.get_backup_restore_config().get_local_backup_base_path()
    local_backup_folder_path = f"{bnr_base_path}/{lab_type}"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Capture the state of software releases (or patches for older versions) before backup
    current_version = CloudPlatformVersionManager.get_sw_version()
    if current_version.is_after_or_equal_to(CloudPlatformSoftwareVersion.STARLINGX_10_0):
        get_logger().log_info("Getting software list (24.09+)")
        sw_list = SoftwareListKeywords(ssh_connection).get_software_list().get_software_lists()
        info_list = [f"{sw.get_release()}:{sw.get_state()}" for sw in sw_list]
    else:
        get_logger().log_info("Getting sw-patch query (pre-24.09)")
        sw_patch_output = SwPatchQueryKeywords(ssh_connection).get_sw_patch_query()
        info_list = [f"{patch.get_patch_id()}:{patch.get_state()}" for patch in sw_patch_output.get_patches()]

    FileKeywords(ssh_connection).create_file_with_echo("/tmp/backup_software_info.txt", "\n".join(info_list))

    # Prechecks Before Back-Up:
    get_logger().log_info("Performing pre-checks before back up")
    
    
    #  Validate pod health 
    get_logger().log_info("Validating pod health across all namespaces")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    healthy_status = ["Running", "Succeeded", "Completed"]
    pods_healthy = kubectl_pods.wait_for_all_pods_status(expected_statuses=healthy_status, timeout=300)
    validate_equals(pods_healthy, True, "All pods health validation")
    
    #  Validate no alarms are present
    get_logger().log_info("Validating no alarms are present")
    AlarmListKeywords(ssh_connection).wait_for_all_alarms_cleared()
    
    #  Validate all apps are healthy and applied
    get_logger().log_info("Validating application health")
    app_healthy_status = ["applied", "uploaded"]
    SystemApplicationListKeywords(ssh_connection).validate_all_apps_status(app_healthy_status)
    
    get_logger().log_info("All cluster health validations passed - Ready for Backup")

    get_logger().log_info("Delete old backup files if present in back up directory")
    backup_files = FileKeywords(ssh_connection).get_files_in_dir(backup_dir)
    for backup_file in backup_files:
        if "backup" in backup_file:
            get_logger().log_info(f"Deleting old backup file {backup_file}")
            file_exists_post_deletion = FileKeywords(ssh_connection).delete_file(f"{backup_dir}/{backup_file}")
            validate_equals(file_exists_post_deletion, False, "Old Back up file deletion")

    time_kpi_backup = TimeKPI(time.time())
    get_logger().log_info("Run backup ansible playbook")
    ansible_playbook_backup_output = AnsiblePlaybookKeywords(ssh_connection).ansible_playbook_backup(backup_dir)
    validate_equals(ansible_playbook_backup_output, True, "Ansible backup command execution")
    time_kpi_backup.log_elapsed_time(time.time(), "time taken for system backup")

    # Append backup filenames to software info file
    backup_files = [f for f in FileKeywords(ssh_connection).get_files_in_dir(backup_dir) if f.endswith('.tgz')]
    if backup_files:
        BackUpFilesUploadKeywords(ssh_connection).append_backup_files_to_info(backup_files)

    # Copy software info to backup directory
    FileKeywords(ssh_connection).copy_file("/tmp/backup_software_info.txt", f"{backup_dir}/backup_software_info.txt", sudo=True)

    backup_file_upload_status = BackUpFilesUploadKeywords(ssh_connection).backup_file(backup_dir, local_backup_folder_path)

    validate_equals(backup_file_upload_status, True, "Backup file upload to local directory")

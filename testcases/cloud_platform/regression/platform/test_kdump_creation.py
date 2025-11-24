from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.kernel.kernel_keywords import KernelKeywords


@mark.p0
@mark.lab_is_simplex
def test_kdump_file_creation_after_kernel_crash(request):
    """
    Testcase to verify kdump file genrated after kernel crash
    Test Steps:
        - connect to active controller
        - verify if any kdump already present
        - run command echo c > /proc/sysrq-trigger to trigger kernel crash
        - wait for lab to come up after crash reboot
        - verify kdump file generated after kernel crash

    """
    kdump_path = "/var/log/crash"
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()

    # Get the host name of the Active controller
    active_controller_host_name = active_controller.get_host_name()

    get_logger().log_info("Delete old core files if present in crash directory")
    core_files = FileKeywords(ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            get_logger().log_info(f"Deleting old core file {core_file}")
            file_exists_post_deletion = FileKeywords(ssh_connection).delete_file(f"{kdump_path}/{core_file}")
            validate_equals(file_exists_post_deletion, False, "Old core file deletion")

    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime("controller-0")

    get_logger().log_info("Trigger kernel crash")
    KernelKeywords(ssh_connection).trigger_kernel_crash()

    get_logger().log_info("wait for lab to come up after crash reboot")
    is_reboot_successful = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(active_controller_host_name, pre_uptime_of_host, 2400)
    validate_equals(is_reboot_successful, True, "crash reboot")

    get_logger().log_info("verify kdump file generated after kernel crash")
    core_files = FileKeywords(ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            file_exists = FileKeywords(ssh_connection).file_exists(f"{kdump_path}/{core_file}")

    validate_equals(file_exists, True, "kdump file created")

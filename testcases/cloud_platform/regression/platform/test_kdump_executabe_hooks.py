from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.date.date_keywords import DateKeywords
from keywords.linux.grep.grep_keywords import GrepKeywords
from keywords.linux.kernel.kernel_keywords import KernelKeywords


def delete_kdump_files(ssh_connection: SSHConnection, kdump_path: str) -> None:
    """
    Delete old core files from kdump directory.

    Args:
        ssh_connection (SSHConnection): SSH connection to the host
        kdump_path (str): Path to kdump directory
    """
    get_logger().log_info("Delete old core files if present in crash directory")
    core_files = FileKeywords(ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            get_logger().log_info(f"Deleting old core file {core_file}")
            file_exists_post_deletion = FileKeywords(ssh_connection).delete_file(f"{kdump_path}/{core_file}")
            validate_equals(file_exists_post_deletion, False, "Old core file deletion")


@mark.p0
@mark.lab_is_simplex
def test_kdump_excecutable_hooks(request):
    """
    Testcase to verify all pre-hooks and post-hooks are executed during kernel dump
    Test Steps:
        - connect to active controller
        - verify pre-hook.d and post-hook.d present in /etc/kdump
        - create pre-hook and post-hook executable files
        - Trigger kernel panic
        - wait for lab to come up after crash reboot
        - verify kdump file generated after kernel crash
        - Verify all hooks are executed during kdump(pre and post)

    """
    kdump_path = "/var/log/crash"
    kdump_log_path = "/var/log/kdump-test.log"
    pre_hook_success_filepath = "/etc/kdump/pre-hooks.d/test-prehook-success"
    post_hook_success_filepath = "/etc/kdump/post-hooks.d/test-posthook-success"
    pre_hook_success_msg = "Pre-hook executed successfully"
    post_hook_success_msg = "Post-hook executed successfully"

    pre_hook_success_content = f'#!/bin/sh\necho "$(date): {pre_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    post_hook_success_content = f'#!/bin/sh\necho "$(date): {post_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()

    # Get the host name of the Active controller
    active_controller_host_name = active_controller.get_host_name()

    delete_kdump_files(ssh_connection, kdump_path)

    get_logger().log_info("Create pre-hook and post-hook executable files")

    # Create pre-hook and post hook wth proper exit code
    prehook_success_file = FileKeywords(ssh_connection).create_file_with_heredoc(pre_hook_success_filepath, pre_hook_success_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(pre_hook_success_filepath)
    posthook_success_file = FileKeywords(ssh_connection).create_file_with_heredoc(post_hook_success_filepath, post_hook_success_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(post_hook_success_filepath)
    validate_equals(prehook_success_file and posthook_success_file, True, "Creation of pre-hook and post-hook files")

    # Get current timestamp for comparison
    current_time = DateKeywords(ssh_connection).get_current_epochtime()
    get_logger().log_info(f"time stamp before Trigger kernel crash {current_time}")

    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(active_controller_host_name)

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

    get_logger().log_info("Verify all pre-hooks and post-hooks are executed after kdump")

    # Get the last Pre-hook executed successfully message timestamp
    last_pre_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(pre_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_post_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(post_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])

    get_logger().log_info(f"last pre hook execution time {last_pre_hook_timestamp}")
    get_logger().log_info(f"last post hook execution time {last_post_hook_timestamp}")

    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_pre_hook_timestamp)) > int(current_time), True, "Pre-hook execution successful")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_post_hook_timestamp)) > int(current_time), True, "Post-hook execution successful")

    delete_kdump_files(ssh_connection, kdump_path)


@mark.p0
@mark.lab_is_simplex
def test_kdump_successful_and_failed_excecutable_hooks(request):
    """
    Testcase to verify all failed pre-hooks and post-hooks are executed during kernel dump
    Test Steps:
        - connect to active controller
        - verify pre-hook.d and post-hook.d present in /etc/kdump
        - create both successful and failed pre-hook and post-hook executable files
        - Trigger kernel panic
        - wait for lab to come up after crash reboot
        - verify kdump file generated after kernel crash
        - Verify all hooks are executed during kdump(pre and post)

    """
    kdump_path = "/var/log/crash"
    kdump_log_path = "/var/log/kdump-test.log"
    pre_hook_success_filepath = "/etc/kdump/pre-hooks.d/test-prehook-success"
    post_hook_success_filepath = "/etc/kdump/post-hooks.d/test-posthook-success"
    pre_hook_fail_filepath = "/etc/kdump/pre-hooks.d/test-prehook-failed"
    post_hook_fail_filepath = "/etc/kdump/post-hooks.d/test-posthook-failed"
    pre_hook_success_msg = "Pre-hook executed successfully"
    post_hook_success_msg = "Post-hook executed successfully"
    pre_hook_fail_msg = "Pre-hook execution failed"
    post_hook_fail_msg = "Post-hook execution failed"

    pre_hook_success_content = f'#!/bin/sh\necho "$(date): {pre_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    post_hook_success_content = f'#!/bin/sh\necho "$(date): {post_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    pre_hook_fail_content = f'#!/bin/sh\necho "$(date): {pre_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'
    post_hook_fail_content = f'#!/bin/sh\necho "$(date): {post_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()

    # Get the host name of the Active controller
    active_controller_host_name = active_controller.get_host_name()

    delete_kdump_files(ssh_connection, kdump_path)

    get_logger().log_info("Create pre-hook and post-hook executable files")
    # Create pre-hook and post hook wth proper exit code
    prehook_success_file = FileKeywords(ssh_connection).create_file_with_heredoc(pre_hook_success_filepath, pre_hook_success_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(pre_hook_success_filepath)
    posthook_success_file = FileKeywords(ssh_connection).create_file_with_heredoc(post_hook_success_filepath, post_hook_success_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(post_hook_success_filepath)
    # Create pre-hook and post hook with exit code 1
    prehook_fail_file = FileKeywords(ssh_connection).create_file_with_heredoc(pre_hook_fail_filepath, pre_hook_fail_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(pre_hook_fail_filepath)
    posthook_fail_file = FileKeywords(ssh_connection).create_file_with_heredoc(post_hook_fail_filepath, post_hook_fail_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(post_hook_fail_filepath)
    validate_equals(all([prehook_success_file, posthook_success_file, prehook_fail_file, posthook_fail_file]), True, "Creation of pre-hook and post-hook files")

    # Get current timestamp for comparison
    current_time = DateKeywords(ssh_connection).get_current_epochtime()

    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(active_controller_host_name)

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

    get_logger().log_info("Verify all pre-hooks and post-hooks are executed after kdump")
    last_success_pre_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(pre_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_success_post_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(post_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_pre_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(pre_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_post_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(post_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])

    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_success_pre_hook_timestamp)) > int(current_time), True, "Pre-hook execution successful")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_success_post_hook_timestamp)) > int(current_time), True, "Post-hook execution successful")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_fail_pre_hook_timestamp)) > int(current_time), True, "Failed Pre-hook execution")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_fail_post_hook_timestamp)) > int(current_time), True, "Failed Post-hook execution")


@mark.p0
@mark.lab_has_standby_controller
def test_kdump_excecutable_hooks_with_standby_controller(request):
    """
    Testcase to verify all failed pre-hooks and post-hooks are executed during kernel dump on stand-by controller
    Test Steps:
        - connect to active controller
        - verify pre-hook.d and post-hook.d present in /etc/kdump
        - create both successful and failed pre-hook and post-hook executable files
        - Trigger kernel panic
        - wait for lab to come up after crash reboot
        - verify kdump file generated after kernel crash
        - Verify all hooks are executed during kdump(pre and post)
        - ssh to standby controller
        - create both successful and failed pre-hook and post-hook executable files
        - Trigger kernel panic
        - wait for controller-1 to come up after crash reboot
        - verify kdump file generated after kernel crash in standby controller
        - Verify all hooks are executed during kdump(pre and post)


    """
    kdump_path = "/var/log/crash"
    kdump_log_path = "/var/log/kdump-test.log"
    pre_hook_success_filepath = "/etc/kdump/pre-hooks.d/test-prehook-success"
    post_hook_success_filepath = "/etc/kdump/post-hooks.d/test-posthook-success"
    pre_hook_fail_filepath = "/etc/kdump/pre-hooks.d/test-prehook-failed"
    post_hook_fail_filepath = "/etc/kdump/post-hooks.d/test-posthook-failed"
    pre_hook_success_msg = "Pre-hook executed successfully"
    post_hook_success_msg = "Post-hook executed successfully"
    pre_hook_fail_msg = "Pre-hook execution failed"
    post_hook_fail_msg = "Post-hook execution failed"

    pre_hook_success_content = f'#!/bin/sh\necho "$(date): {pre_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    post_hook_success_content = f'#!/bin/sh\necho "$(date): {post_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    pre_hook_fail_content = f'#!/bin/sh\necho "$(date): {pre_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'
    post_hook_fail_content = f'#!/bin/sh\necho "$(date): {post_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    standby_ssh_connection = LabConnectionKeywords().get_standby_controller_ssh()

    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller()

    # Get the host name of the Active controller
    active_controller_host_name = active_controller.get_host_name()
    # Get the host name of the Standby controller
    standby_controller_host_name = standby_controller.get_host_name()

    delete_kdump_files(ssh_connection, kdump_path)

    get_logger().log_info("Create pre-hook and post-hook executable files")

    # Create pre-hook and post hook wth proper exit code
    prehook_success_file = FileKeywords(ssh_connection).create_file_with_heredoc(pre_hook_success_filepath, pre_hook_success_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(pre_hook_success_filepath)
    posthook_success_file = FileKeywords(ssh_connection).create_file_with_heredoc(post_hook_success_filepath, post_hook_success_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(post_hook_success_filepath)
    # Create pre-hook and post hook with exit code 1
    prehook_fail_file = FileKeywords(ssh_connection).create_file_with_heredoc(pre_hook_fail_filepath, pre_hook_fail_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(pre_hook_fail_filepath)
    posthook_fail_file = FileKeywords(ssh_connection).create_file_with_heredoc(post_hook_fail_filepath, post_hook_fail_content, is_sudo=True)
    FileKeywords(ssh_connection).make_executable(post_hook_fail_filepath)
    validate_equals(all([prehook_success_file, posthook_success_file, prehook_fail_file, posthook_fail_file]), True, "Creation of pre-hook and post-hook files")

    # Get current timestamp for comparison
    current_time = DateKeywords(ssh_connection).get_current_time()

    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(active_controller_host_name)
    pre_uptime_standby_host = SystemHostListKeywords(ssh_connection).get_uptime(standby_controller_host_name)

    get_logger().log_info("Trigger kernel crash")
    KernelKeywords(ssh_connection).trigger_kernel_crash()

    get_logger().log_info("wait for lab to come up after crash reboot")
    is_reboot_successful = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(active_controller_host_name, pre_uptime_of_host, 2400)
    validate_equals(is_reboot_successful, True, "crash reboot")

    swact_success = SystemHostSwactKeywords(ssh_connection).host_swact()
    validate_equals(swact_success, True, "Controller Swact")

    get_logger().log_info("verify kdump file generated after kernel crash")
    core_files = FileKeywords(ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            file_exists = FileKeywords(ssh_connection).file_exists(f"{kdump_path}/{core_file}")

    validate_equals(file_exists, True, "kdump file created")

    get_logger().log_info("Verify all pre-hooks and post-hooks are executed after kdump")

    last_success_pre_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(pre_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_success_post_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(post_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_pre_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(pre_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_post_hook_timestamp = GrepKeywords(ssh_connection).grep_and_extract_fields(post_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])

    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_success_pre_hook_timestamp)) > int(current_time), True, "Pre-hook execution successful")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_success_post_hook_timestamp)) > int(current_time), True, "Post-hook execution successful")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_fail_pre_hook_timestamp)) > int(current_time), True, "Failed Pre-hook execution")
    validate_equals(int(DateKeywords(ssh_connection).get_custom_epochtime(last_fail_post_hook_timestamp)) > int(current_time), True, "Failed Post-hook execution")

    delete_kdump_files(ssh_connection, kdump_path)

    delete_kdump_files(standby_ssh_connection, kdump_path)
    get_logger().log_info("Create pre-hook and post-hook executable files in standby controller")

    # Create pre-hook and post hook wth proper exit code

    prehook_success_file = FileKeywords(standby_ssh_connection).create_file_with_heredoc(pre_hook_success_filepath, pre_hook_success_content, is_sudo=True)
    FileKeywords(standby_ssh_connection).make_executable(pre_hook_success_filepath)
    posthook_success_file = FileKeywords(standby_ssh_connection).create_file_with_heredoc(post_hook_success_filepath, post_hook_success_content, is_sudo=True)
    FileKeywords(standby_ssh_connection).make_executable(post_hook_success_filepath)
    # Create pre-hook and post hook with exit code 1
    prehook_fail_file = FileKeywords(standby_ssh_connection).create_file_with_heredoc(pre_hook_fail_filepath, pre_hook_fail_content, is_sudo=True)
    FileKeywords(standby_ssh_connection).make_executable(pre_hook_fail_filepath)
    posthook_fail_file = FileKeywords(standby_ssh_connection).create_file_with_heredoc(post_hook_fail_filepath, post_hook_fail_content, is_sudo=True)
    FileKeywords(standby_ssh_connection).make_executable(post_hook_fail_filepath)
    validate_equals(all([prehook_success_file, posthook_success_file, prehook_fail_file, posthook_fail_file]), True, "Creation of pre-hook and post-hook files")

    # Get current timestamp for comparison
    current_time = DateKeywords(standby_ssh_connection).get_current_time()

    # pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime("controller-1")

    get_logger().log_info("Trigger kernel crash")
    KernelKeywords(standby_ssh_connection).trigger_kernel_crash()

    get_logger().log_info("wait for lab to come up after crash reboot")
    is_reboot_successful = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(standby_controller_host_name, pre_uptime_standby_host, 2400)
    validate_equals(is_reboot_successful, True, "crash reboot")

    get_logger().log_info("verify kdump file generated after kernel crash")
    core_files = FileKeywords(standby_ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            file_exists = FileKeywords(standby_ssh_connection).file_exists(f"{kdump_path}/{core_file}")

    validate_equals(file_exists, True, "kdump file created")

    get_logger().log_info("Verify all pre-hooks and post-hooks are executed after kdump")

    # Get the last Pre-hook executed successfully message timestamp
    last_success_pre_hook_timestamp = GrepKeywords(standby_ssh_connection).grep_and_extract_fields(pre_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_success_post_hook_timestamp = GrepKeywords(standby_ssh_connection).grep_and_extract_fields(post_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_pre_hook_timestamp = GrepKeywords(standby_ssh_connection).grep_and_extract_fields(pre_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_post_hook_timestamp = GrepKeywords(standby_ssh_connection).grep_and_extract_fields(post_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])

    validate_equals(int(DateKeywords(standby_ssh_connection).get_custom_epochtime(last_success_pre_hook_timestamp)) > int(current_time), True, "Pre-hook execution successful")
    validate_equals(int(DateKeywords(standby_ssh_connection).get_custom_epochtime(last_success_post_hook_timestamp)) > int(current_time), True, "Post-hook execution successful")
    validate_equals(int(DateKeywords(standby_ssh_connection).get_custom_epochtime(last_fail_pre_hook_timestamp)) > int(current_time), True, "Failed Pre-hook execution")
    validate_equals(int(DateKeywords(standby_ssh_connection).get_custom_epochtime(last_fail_post_hook_timestamp)) > int(current_time), True, "Failed Post-hook execution")

    delete_kdump_files(standby_ssh_connection, kdump_path)


@mark.p0
@mark.lab_has_compute
def test_kdump_excecutable_hooks_compute_host(request):
    """
    Testcase to verify all pre-hooks and post-hooks are executed during kernel dump
    Test Steps:
        - connect to compute node
        - verify pre-hook.d and post-hook.d present in /etc/kdump
        - create pre-hook and post-hook executable files
        - Trigger kernel panic
        - wait for compute to come up after crash reboot
        - verify kdump file generated after kernel crash
        - Verify all hooks are executed during kdump(pre and post)

    """
    kdump_path = "/var/log/crash"
    kdump_log_path = "/var/log/kdump-test.log"
    pre_hook_success_filepath = "/etc/kdump/pre-hooks.d/test-prehook-success"
    post_hook_success_filepath = "/etc/kdump/post-hooks.d/test-posthook-success"
    pre_hook_fail_filepath = "/etc/kdump/pre-hooks.d/test-prehook-failed"
    post_hook_fail_filepath = "/etc/kdump/post-hooks.d/test-posthook-failed"
    pre_hook_success_msg = "Pre-hook executed successfully"
    post_hook_success_msg = "Post-hook executed successfully"
    pre_hook_fail_msg = "Pre-hook execution failed"
    post_hook_fail_msg = "Post-hook execution failed"

    pre_hook_success_content = f'#!/bin/sh\necho "$(date): {pre_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    post_hook_success_content = f'#!/bin/sh\necho "$(date): {post_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    pre_hook_fail_content = f'#!/bin/sh\necho "$(date): {pre_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'
    post_hook_fail_content = f'#!/bin/sh\necho "$(date): {post_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    computes = SystemHostListKeywords(ssh_connection).get_computes()

    assert len(computes) > 0, "No computes were found"

    # get the first compute
    compute = computes[0]
    compute_ssh_connection = LabConnectionKeywords().get_compute_ssh(compute.get_host_name())

    # get the prev uptime of the host so we can be sure it re-started
    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(compute.get_host_name())

    delete_kdump_files(compute_ssh_connection, kdump_path)

    get_logger().log_info("Create pre-hook and post-hook executable files")

    # Create pre-hook and post hook wth proper exit code
    prehook_success_file = FileKeywords(compute_ssh_connection).create_file_with_heredoc(pre_hook_success_filepath, pre_hook_success_content, is_sudo=True)
    FileKeywords(compute_ssh_connection).make_executable(pre_hook_success_filepath)
    posthook_success_file = FileKeywords(compute_ssh_connection).create_file_with_heredoc(post_hook_success_filepath, post_hook_success_content, is_sudo=True)
    FileKeywords(compute_ssh_connection).make_executable(post_hook_success_filepath)
    # Create pre-hook and post hook with exit code 1
    prehook_fail_file = FileKeywords(compute_ssh_connection).create_file_with_heredoc(pre_hook_fail_filepath, pre_hook_fail_content, is_sudo=True)
    FileKeywords(compute_ssh_connection).make_executable(pre_hook_fail_filepath)
    posthook_fail_file = FileKeywords(compute_ssh_connection).create_file_with_heredoc(post_hook_fail_filepath, post_hook_fail_content, is_sudo=True)
    FileKeywords(compute_ssh_connection).make_executable(post_hook_fail_filepath)
    validate_equals(all([prehook_success_file, posthook_success_file, prehook_fail_file, posthook_fail_file]), True, "Creation of pre-hook and post-hook files")

    # Get current timestamp for comparison
    current_time = DateKeywords(compute_ssh_connection).get_current_time()

    get_logger().log_info("Trigger kernel crash")
    KernelKeywords(compute_ssh_connection).trigger_kernel_crash()

    get_logger().log_info("wait for lab to come up after crash reboot")
    is_reboot_successful = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(compute.get_host_name(), pre_uptime_of_host, 2400)
    validate_equals(is_reboot_successful, True, "crash reboot")

    get_logger().log_info("verify kdump file generated after kernel crash")
    core_files = FileKeywords(compute_ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            file_exists = FileKeywords(compute_ssh_connection).file_exists(f"{kdump_path}/{core_file}")

    validate_equals(file_exists, True, "kdump file created")

    get_logger().log_info("Verify all pre-hooks and post-hooks are executed after kdump")

    # Get the last Pre-hook executed successfully message timestamp
    last_success_pre_hook_timestamp = GrepKeywords(compute_ssh_connection).grep_and_extract_fields(pre_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_success_post_hook_timestamp = GrepKeywords(compute_ssh_connection).grep_and_extract_fields(post_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_pre_hook_timestamp = GrepKeywords(compute_ssh_connection).grep_and_extract_fields(pre_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_post_hook_timestamp = GrepKeywords(compute_ssh_connection).grep_and_extract_fields(post_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])

    validate_equals(int(DateKeywords(compute_ssh_connection).get_custom_epochtime(last_success_pre_hook_timestamp)) > int(current_time), True, "Pre-hook execution successful")
    validate_equals(int(DateKeywords(compute_ssh_connection).get_custom_epochtime(last_success_post_hook_timestamp)) > int(current_time), True, "Post-hook execution successful")
    validate_equals(int(DateKeywords(compute_ssh_connection).get_custom_epochtime(last_fail_pre_hook_timestamp)) > int(current_time), True, "Failed Pre-hook execution")
    validate_equals(int(DateKeywords(compute_ssh_connection).get_custom_epochtime(last_fail_post_hook_timestamp)) > int(current_time), True, "Failed Post-hook execution")

    delete_kdump_files(compute_ssh_connection, kdump_path)


@mark.p0
@mark.lab_has_storage
def test_kdump_excecutable_hooks_storage_host(request):
    """
    Testcase to verify all pre-hooks and post-hooks are executed during kernel dump
    Test Steps:
        - connect to storage node
        - verify pre-hook.d and post-hook.d present in /etc/kdump
        - create pre-hook and post-hook executable files
        - Trigger kernel panic
        - wait for storage to come up after crash reboot
        - verify kdump file generated after kernel crash
        - Verify all hooks are executed during kdump(pre and post)

    """
    kdump_path = "/var/log/crash"
    kdump_log_path = "/var/log/kdump-test.log"
    pre_hook_success_filepath = "/etc/kdump/pre-hooks.d/test-prehook-success"
    post_hook_success_filepath = "/etc/kdump/post-hooks.d/test-posthook-success"
    pre_hook_fail_filepath = "/etc/kdump/pre-hooks.d/test-prehook-failed"
    post_hook_fail_filepath = "/etc/kdump/post-hooks.d/test-posthook-failed"
    pre_hook_success_msg = "Pre-hook executed successfully"
    post_hook_success_msg = "Post-hook executed successfully"
    pre_hook_fail_msg = "Pre-hook execution failed"
    post_hook_fail_msg = "Post-hook execution failed"

    pre_hook_success_content = f'#!/bin/sh\necho "$(date): {pre_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    post_hook_success_content = f'#!/bin/sh\necho "$(date): {post_hook_success_msg}" >> /var/log/kdump-test.log\nexit 0'
    pre_hook_fail_content = f'#!/bin/sh\necho "$(date): {pre_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'
    post_hook_fail_content = f'#!/bin/sh\necho "$(date): {post_hook_fail_msg}" >> /var/log/kdump-test.log\nexit 1'

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    storages = SystemHostListKeywords(ssh_connection).get_storages()

    assert len(storages) > 0, "No storage node were found"

    # get the first storage
    storage = storages[0]
    storage_ssh_connection = LabConnectionKeywords().get_compute_ssh(storage.get_host_name())

    # get the prev uptime of the host so we can be sure it re-started
    pre_uptime_of_host = SystemHostListKeywords(ssh_connection).get_uptime(storage.get_host_name())

    delete_kdump_files(storage_ssh_connection, kdump_path)

    get_logger().log_info("Create pre-hook and post-hook executable files")

    # Create pre-hook and post hook wth proper exit code
    prehook_success_file = FileKeywords(storage_ssh_connection).create_file_with_heredoc(pre_hook_success_filepath, pre_hook_success_content, is_sudo=True)
    FileKeywords(storage_ssh_connection).make_executable(pre_hook_success_filepath)
    posthook_success_file = FileKeywords(storage_ssh_connection).create_file_with_heredoc(post_hook_success_filepath, post_hook_success_content, is_sudo=True)
    FileKeywords(storage_ssh_connection).make_executable(post_hook_success_filepath)
    # Create pre-hook and post hook with exit code 1
    prehook_fail_file = FileKeywords(storage_ssh_connection).create_file_with_heredoc(pre_hook_fail_filepath, pre_hook_fail_content, is_sudo=True)
    FileKeywords(storage_ssh_connection).make_executable(pre_hook_fail_filepath)
    posthook_fail_file = FileKeywords(storage_ssh_connection).create_file_with_heredoc(post_hook_fail_filepath, post_hook_fail_content, is_sudo=True)
    FileKeywords(storage_ssh_connection).make_executable(post_hook_fail_filepath)
    validate_equals(all([prehook_success_file, posthook_success_file, prehook_fail_file, posthook_fail_file]), True, "Creation of pre-hook and post-hook files")

    # Get current timestamp for comparison
    current_time = DateKeywords(storage_ssh_connection).get_current_time()

    get_logger().log_info("Trigger kernel crash")
    KernelKeywords(storage_ssh_connection).trigger_kernel_crash()

    get_logger().log_info("wait for lab to come up after crash reboot")
    is_reboot_successful = SystemHostRebootKeywords(ssh_connection).wait_for_force_reboot(storage.get_host_name(), pre_uptime_of_host, 2400)
    validate_equals(is_reboot_successful, True, "crash reboot")

    get_logger().log_info("verify kdump file generated after kernel crash")
    core_files = FileKeywords(storage_ssh_connection).get_files_in_dir(kdump_path)
    for core_file in core_files:
        if "core" in core_file:
            file_exists = FileKeywords(storage_ssh_connection).file_exists(f"{kdump_path}/{core_file}")

    validate_equals(file_exists, True, "kdump file created")

    get_logger().log_info("Verify all pre-hooks and post-hooks are executed after kdump")

    # Get the last Pre-hook executed successfully message timestamp
    last_success_pre_hook_timestamp = GrepKeywords(storage_ssh_connection).grep_and_extract_fields(pre_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_success_post_hook_timestamp = GrepKeywords(storage_ssh_connection).grep_and_extract_fields(post_hook_success_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_pre_hook_timestamp = GrepKeywords(storage_ssh_connection).grep_and_extract_fields(pre_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    last_fail_post_hook_timestamp = GrepKeywords(storage_ssh_connection).grep_and_extract_fields(post_hook_fail_msg, kdump_log_path, 1, [1, 2, 3, 4, 5])
    validate_equals(int(DateKeywords(storage_ssh_connection).get_custom_epochtime(last_success_pre_hook_timestamp)) > int(current_time), True, "Pre-hook execution successful")
    validate_equals(int(DateKeywords(storage_ssh_connection).get_custom_epochtime(last_success_post_hook_timestamp)) > int(current_time), True, "Post-hook execution successful")
    validate_equals(int(DateKeywords(storage_ssh_connection).get_custom_epochtime(last_fail_pre_hook_timestamp)) > int(current_time), True, "Failed Pre-hook execution")
    validate_equals(int(DateKeywords(storage_ssh_connection).get_custom_epochtime(last_fail_post_hook_timestamp)) > int(current_time), True, "Failed Post-hook execution")

    delete_kdump_files(storage_ssh_connection, kdump_path)

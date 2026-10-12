from typing import Optional

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.collect_logs.collect_logs_keywords import CollectLogsKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.files.file_keywords import FileKeywords

#
# These exercise host-level `collect` on a non-DC system (simplex/standard).
# Collection is driven through the SAME CollectLogsKeywords used by the DC
# collect-log suite — the keyword layer is common to both; only the subject
# (hosts here vs subclouds in DC) differs. No DC-specific logic is used.

# Default collect bundle directory on the controller.
COLLECT_BUNDLE_DIR = "/scratch"
# Target /scratch usage percentage for the full-scratch error test; must exceed
# collect's 75% refusal threshold.
SCRATCH_FILL_PERCENTAGE = 77


def _remove_bundle(ssh: SSHConnection, tar_path: Optional[str]) -> None:
    """Delete a collected tar bundle if one was produced.

    Args:
        ssh (SSHConnection): SSH to the active controller.
        tar_path (Optional[str]): Path to the collected .tar bundle (may be None).
    """
    if tar_path:
        get_logger().log_info(f"Removing collected bundle {tar_path}")
        FileKeywords(ssh).delete_file(tar_path)


@mark.p1
def test_collect_all_logs(request):
    """Collect logs from all hosts on the system and verify the bundle.

    Test Steps:
        - Run ``collect --all`` on the active controller.
        - Verify every host is reported collected and present in the tar.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    hosts = SystemHostListKeywords(ssh).get_system_host_list().get_host_names()
    get_logger().log_info(f"Hosts on system: {hosts}")

    collect_kw = CollectLogsKeywords(ssh)
    collect_output = collect_kw.collect(all_hosts=True)
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(ssh, tar_path))

    get_logger().log_info("Verify all hosts were collected")
    for host in hosts:
        validate_equals(collect_output.is_name_collected(host), True, f"Expected host {host} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, hosts)


@mark.p3
def test_invalid_password_collect_logs():
    """Collect from all hosts with a wrong password is rejected.

    Test Steps:
        - Run ``collect --all`` supplying a wrong password at the sudo prompt.
        - Verify collect reports an invalid-password error and does not proceed.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    collect_kw = CollectLogsKeywords(ssh)

    get_logger().log_info("Collect logs for all hosts with a wrong password")
    collect_output = collect_kw.collect(all_hosts=True, password="wrong_password", validate_rc=False)

    get_logger().log_info("Verify collect rejected the invalid password")
    validate_str_contains(collect_output.get_output_text().lower(), "invalid password", f"collect should fail with a wrong password, got: {collect_output.get_output_text()}")


@mark.p2
def test_error_handling_full_scratch(request):
    """Collect is refused when the controller's /scratch is over 75% used.

    Test Steps:
        - Fill /scratch on the active controller to ~77%.
        - Run ``collect --all``.
        - Verify collect refuses because /scratch usage must be below 75%.

    Teardown:
        - Remove the fill file and any collected bundle.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    collect_kw = CollectLogsKeywords(ssh)
    tar_holder = {}

    get_logger().log_info(f"Fill {COLLECT_BUNDLE_DIR} on the active controller to {SCRATCH_FILL_PERCENTAGE}%")
    fill_file = FileKeywords(ssh).fill_disk_to_percentage(COLLECT_BUNDLE_DIR, SCRATCH_FILL_PERCENTAGE)

    def teardown():
        FileKeywords(ssh).delete_file(fill_file)
        _remove_bundle(ssh, tar_holder.get("path"))

    request.addfinalizer(teardown)

    get_logger().log_info("Collect logs for all hosts with /scratch over threshold")
    collect_output = collect_kw.collect(all_hosts=True, validate_rc=False)
    tar_holder["path"] = collect_output.get_tar_file_path()

    get_logger().log_info("Verify collect refused due to insufficient /scratch space")
    output_text = collect_output.get_output_text()
    validate_str_contains(output_text, "Not enough space on remote device", f"Expected 'Not enough space on remote device' in collect output: {output_text}")
    validate_str_contains(output_text, "usage must be below 75%", f"Expected 'usage must be below 75%' in collect output: {output_text}")


@mark.p2
@mark.lab_has_standby_controller
def test_error_handling_unavailable_host(request):
    """Collect reports an unreachable host and collects the rest.

    exist to reboot) — gated by @mark.lab_has_standby_controller.

    Test Steps:
        - Reboot a non-active host and wait until it is offline.
        - Run ``collect --all``.
        - Verify the rebooted host reports unreachable and is not collected,
          while the remaining hosts are collected and present in the tar.

    Teardown:
        - Remove any collected bundle.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    host_list_kw = SystemHostListKeywords(ssh)
    collect_kw = CollectLogsKeywords(ssh)
    tar_holder = {}

    all_hosts = host_list_kw.get_system_host_list().get_host_names()
    # get_active_controller() (the keyword) fetches the capabilities column so
    # the active controller resolves correctly; the plain host-list output does
    # not carry capabilities and cannot identify the active controller.
    active_controller = host_list_kw.get_active_controller().get_host_name()
    candidates = [h for h in all_hosts if h != active_controller]
    # Pick deterministically (first non-active host, sorted) so a failure always
    # reproduces the same scenario — avoids the flakiness of random.choice.
    reboot_host = sorted(candidates)[0]
    remaining_hosts = [h for h in all_hosts if h != reboot_host]
    get_logger().log_info(f"active={active_controller} reboot={reboot_host} remaining={remaining_hosts}")

    def teardown():
        _remove_bundle(ssh, tar_holder.get("path"))

    request.addfinalizer(teardown)

    get_logger().log_info(f"Force reboot host {reboot_host} and wait for it to go offline")
    # Ungraceful 'sudo reboot -f' on the target host (via its own SSH), fired
    # without waiting for a response — the reboot drops the SSH session, so the
    # no-wait variant avoids blocking on a reconnect to the downed host.
    host_ssh = LabConnectionKeywords().get_ssh_for_hostname(reboot_host)
    SystemHostRebootKeywords(host_ssh).host_force_reboot_no_wait()
    host_list_kw.wait_for_host_availability(reboot_host, ["offline"], timeout=600, polling_sleep_time=15)

    get_logger().log_info("Collect logs on all hosts")
    collect_output = collect_kw.collect(all_hosts=True, validate_rc=False)
    tar_holder["path"] = collect_output.get_tar_file_path()

    get_logger().log_info(f"Verify host {reboot_host} reported unreachable")
    validate_str_contains(collect_output.get_output_text(), reboot_host, f"Expected an unreachable reference to {reboot_host}: {collect_output.get_output_text()}")
    validate_equals(collect_output.is_name_collected(reboot_host), False, f"Host {reboot_host} is offline and should not be collected: {collect_output.get_collected_names()}")

    get_logger().log_info(f"Verify remaining hosts {remaining_hosts} were collected")
    for host in remaining_hosts:
        validate_equals(collect_output.is_name_collected(host), True, f"Expected host {host} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_holder["path"], "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_holder["path"], remaining_hosts)

from typing import List, Optional, Tuple

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_not_none, validate_str_contains
from keywords.bmc.ipmitool.chassis.power.ipmitool_chassis_power_keywords import IPMIToolChassisPowerKeywords
from keywords.cloud_platform.collect_logs.collect_logs_keywords import CollectLogsKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import SubcloudPickerKeywords
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords

#
# Collection is driven through CollectLogsKeywords (wraps the `collect` CLI) and
# subcloud selection reuses SubcloudPickerKeywords. The collect-output regexes
# live in CollectLogsOutput and will be tuned after manual lab verification.

# Scratch over-threshold alarm id used by the full-scratch error-handling test.
SCRATCH_ALARM_ID = "100.104"
# Target /scratch usage percentage for the full-scratch (host) error test; must
# exceed collect's 75% refusal threshold.
SCRATCH_FILL_PERCENTAGE = 77
# Default collect bundle directory on the controller.
COLLECT_BUNDLE_DIR = "/scratch"
# File consumed by `collect --continue`.
COLLECT_CONTINUE_LIST = "/tmp/collect_continue.lst"


def _remove_bundle(central_ssh: SSHConnection, tar_path: Optional[str]) -> None:
    """Delete a collected tar bundle if one was produced.

    Args:
        central_ssh (SSHConnection): SSH to the central/active controller.
        tar_path (Optional[str]): Path to the collected .tar bundle (may be None).
    """
    if tar_path:
        get_logger().log_info(f"Removing collected bundle {tar_path}")
        FileKeywords(central_ssh).delete_file(tar_path)


def _pick_online_subclouds(count: int) -> Tuple[SSHConnection, List[str]]:
    """Pick ``count`` online subclouds from the central cloud.

    Args:
        count (int): Number of subclouds required.

    Returns:
        Tuple[SSHConnection, List[str]]: (central_ssh, [subcloud_name, ...]).
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    results = SubcloudPickerKeywords(central_ssh).pick_all(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    )
    names = [r.get_name() for r in results[:count]]
    return central_ssh, names


@mark.p3
@mark.lab_has_subcloud
def test_log_collection_subcloud(request):
    """Collect logs for all hosts on a single subcloud and verify the bundle.

    Test Steps:
        - Pick an online subcloud from the central cloud.
        - Run ``collect --subcloud <name>``.
        - Verify the collect output reports exactly that subcloud.
        - Verify the subcloud's logs are present inside the produced tar bundle.

    Teardown:
        - Remove the collected tar bundle from /scratch/ on the central cloud.
    """
    central_ssh, result = SubcloudPickerKeywords.pick_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    )
    subcloud_name = result.get_name()
    get_logger().log_info(f"Selected subcloud for collect: {subcloud_name}")

    collect_kw = CollectLogsKeywords(central_ssh)

    get_logger().log_info(f"Collect logs for all hosts on subcloud {subcloud_name}")
    collect_output = collect_kw.collect(subcloud=subcloud_name)
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(central_ssh, tar_path))

    get_logger().log_info(f"Verify only subcloud {subcloud_name} was collected")
    validate_equals(collect_output.is_name_collected(subcloud_name), True, f"Expected subcloud {subcloud_name} in collect output, got: {collect_output.get_collected_names()}")

    get_logger().log_info(f"Verify collected logs in tar bundle {tar_path}")
    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, [subcloud_name])


@mark.p3
@mark.lab_has_min_2_subclouds
def test_subclouds_log_collection(request):
    """Collect logs for two subclouds in parallel and verify the bundle.

    Test Steps:
        - Pick two online subclouds.
        - Run ``collect --subcloud <a> <b>``.
        - Verify 'please standby' appears in the output.
        - Verify both subclouds are reported collected and present in the tar.
    """
    central_ssh, subclouds = _pick_online_subclouds(2)
    get_logger().log_info(f"Selected subclouds for collect: {subclouds}")

    collect_kw = CollectLogsKeywords(central_ssh)
    collect_output = collect_kw.collect(subcloud=subclouds)
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(central_ssh, tar_path))

    get_logger().log_info("Verify 'please standby' is in collect output")
    validate_str_contains(collect_output.get_output_text(), "please standby", "'please standby' not found in collect output")

    get_logger().log_info(f"Verify subclouds {subclouds} were collected")
    for name in subclouds:
        validate_equals(collect_output.is_name_collected(name), True, f"Expected subcloud {name} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, subclouds)


@mark.p3
@mark.lab_has_min_2_subclouds
def test_parallel_vs_inline_subclouds_log_collection(request):
    """Compare parallel vs inline collect execution time for two subclouds.

    Test Steps:
        - Pick two online subclouds.
        - Collect in parallel (default) and record execution time.
        - Collect again with ``--inline`` and record execution time.
        - Verify both bundles contain the subclouds.
        - Verify inline execution time is not faster than parallel.
    """
    central_ssh, subclouds = _pick_online_subclouds(2)
    get_logger().log_info(f"Selected subclouds for collect: {subclouds}")

    collect_kw = CollectLogsKeywords(central_ssh)
    bundles = []
    request.addfinalizer(lambda: [_remove_bundle(central_ssh, p) for p in bundles])

    get_logger().log_info(f"Collect (parallel) on subclouds {subclouds}")
    parallel_output = collect_kw.collect(subcloud=subclouds)
    parallel_tar = parallel_output.get_tar_file_path()
    bundles.append(parallel_tar)
    parallel_time = parallel_output.get_execution_time()
    validate_not_none(parallel_time, "Unable to get execution time for parallel collection")
    validate_not_none(parallel_tar, "parallel collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(parallel_tar, subclouds)

    get_logger().log_info(f"Collect (inline) on subclouds {subclouds}")
    inline_output = collect_kw.collect(subcloud=subclouds, inline=True)
    inline_tar = inline_output.get_tar_file_path()
    bundles.append(inline_tar)
    inline_time = inline_output.get_execution_time()
    validate_not_none(inline_time, "Unable to get execution time for inline collection")
    validate_not_none(inline_tar, "inline collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(inline_tar, subclouds)

    get_logger().log_info(f"parallel={parallel_time}s inline={inline_time}s")
    validate_equals(bool(inline_time >= parallel_time), True, "Inline execution time is faster than parallel which is not expected")


@mark.p3
@mark.lab_has_subcloud
def test_all_subclouds_log_collection(request):
    """Collect logs for all subclouds and verify the bundle.

    Test Steps:
        - Discover all online subclouds.
        - Run ``collect --all --subcloud all``.
        - Verify every subcloud is reported collected and present in the tar.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    results = SubcloudPickerKeywords(central_ssh).pick_all(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
    )
    all_subclouds = [r.get_name() for r in results]
    get_logger().log_info(f"All online subclouds: {all_subclouds}")

    collect_kw = CollectLogsKeywords(central_ssh)
    collect_output = collect_kw.collect(all_hosts=True, subcloud="all")
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(central_ssh, tar_path))

    get_logger().log_info("Verify all subclouds were collected")
    for name in all_subclouds:
        validate_equals(collect_output.is_name_collected(name), True, f"Expected subcloud {name} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, all_subclouds)


@mark.p3
@mark.lab_has_min_2_subclouds
def test_list_subclouds_log_collection(request):
    """Collect logs for subclouds using ``--list`` and verify the bundle.

    Test Steps:
        - Pick up to two online subclouds.
        - Run ``collect --subcloud --list <a> <b>``.
        - Verify the subclouds are reported collected and present in the tar.
    """
    central_ssh, subclouds = _pick_online_subclouds(2)
    get_logger().log_info(f"Selected subclouds for collect --list: {subclouds}")

    collect_kw = CollectLogsKeywords(central_ssh)
    collect_output = collect_kw.collect(subcloud_list=subclouds)
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(central_ssh, tar_path))

    get_logger().log_info(f"Verify subclouds {subclouds} were collected")
    for name in subclouds:
        validate_equals(collect_output.is_name_collected(name), True, f"Expected subcloud {name} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, subclouds)


@mark.p3
@mark.lab_has_min_2_subclouds
def test_subclouds_log_collection_by_prefix(request):
    """Collect logs for subclouds with a custom bundle name prefix.

    Test Steps:
        - Pick up to two online subclouds.
        - Run ``collect --subcloud --list <names> --name <prefix>``.
        - Verify the produced bundle name starts with the prefix.
        - Verify the subclouds are present in the tar.
    """
    collect_file_name = "joe"
    central_ssh, subclouds = _pick_online_subclouds(2)
    get_logger().log_info(f"Selected subclouds for prefixed collect: {subclouds}")

    collect_kw = CollectLogsKeywords(central_ssh)
    collect_output = collect_kw.collect(subcloud_list=subclouds, collect_file_name=collect_file_name)
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(central_ssh, tar_path))

    get_logger().log_info(f"Verify collected bundle name contains prefix '{collect_file_name}'")
    validate_not_none(tar_path, "collect did not report a tar bundle path")
    validate_str_contains(tar_path, collect_file_name, f"Expected bundle name to contain '{collect_file_name}', got {tar_path}")

    collect_kw.verify_collected_names_in_tar(tar_path, subclouds)


@mark.p2
@mark.lab_has_min_2_subclouds
def test_error_handling_full_scratch_some_subclouds(request):
    """Collect skips a subcloud whose /scratch is over the threshold.

    Test Steps:
        - Pick two online subclouds; designate one as the full-scratch subcloud.
        - Fill /scratch on that subcloud and wait for alarm 100.104.
        - Run ``collect --subcloud <good> <full>``.
        - Verify the full-scratch subcloud is NOT collected while the other is.

    Teardown:
        - Remove the collected bundle and the fill file from the subcloud.
    """
    central_ssh, subclouds = _pick_online_subclouds(2)
    good_subcloud, full_subcloud = subclouds[0], subclouds[1]
    get_logger().log_info(f"good={good_subcloud} full_scratch={full_subcloud}")

    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(full_subcloud)
    fill_file = FileKeywords(subcloud_ssh).create_file_to_fill_disk_space(dest_dir="/scratch")

    collect_kw = CollectLogsKeywords(central_ssh)
    tar_holder = {}

    def teardown():
        _remove_bundle(central_ssh, tar_holder.get("path"))
        FileKeywords(subcloud_ssh).delete_file(fill_file)

    request.addfinalizer(teardown)

    get_logger().log_info(f"Wait for scratch alarm {SCRATCH_ALARM_ID} on {full_subcloud}")
    alarm_kw = AlarmListKeywords(subcloud_ssh)
    validate_equals_with_retry(
        lambda: alarm_kw.is_alarm_present(SCRATCH_ALARM_ID),
        True,
        f"Scratch alarm {SCRATCH_ALARM_ID} present on {full_subcloud}",
        timeout=240,
        polling_sleep_time=10,
    )

    get_logger().log_info(f"Collect logs for subclouds {subclouds}")
    collect_output = collect_kw.collect(subcloud=subclouds)
    tar_holder["path"] = collect_output.get_tar_file_path()

    get_logger().log_info(f"Verify full-scratch subcloud {full_subcloud} was NOT collected")
    validate_equals(collect_output.is_name_collected(full_subcloud), False, f"Subcloud {full_subcloud} is over /scratch threshold and should not be collected: {collect_output.get_output_text()}")

    validate_not_none(tar_holder["path"], "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_holder["path"], [good_subcloud])


@mark.p2
@mark.lab_has_min_2_subclouds
def test_error_handling_unavailable_subcloud(request):
    """Collect reports an unreachable subcloud and collects the rest.

    Test Steps:
        - Pick two online subclouds; designate one to power off.
        - Power the subcloud off via BMC/IPMI and wait until offline.
        - Run ``collect --subcloud <good> <offline>``.
        - Power the subcloud back on and wait until online.
        - Verify the offline subcloud reports unreachable and is not collected,
          while the available subcloud is collected.
    """
    central_ssh, subclouds = _pick_online_subclouds(2)
    good_subcloud, offline_subcloud = subclouds[0], subclouds[1]
    get_logger().log_info(f"good={good_subcloud} offline={offline_subcloud}")

    power_kw = IPMIToolChassisPowerKeywords(central_ssh, host_name=None)
    sc_list_kw = DcManagerSubcloudListKeywords(central_ssh)
    collect_kw = CollectLogsKeywords(central_ssh)
    tar_holder = {}

    def teardown():
        _remove_bundle(central_ssh, tar_holder.get("path"))

    request.addfinalizer(teardown)

    get_logger().log_info(f"Power off subcloud {offline_subcloud} via IPMI")
    power_kw.power_off_subcloud(offline_subcloud)
    # Wait for the subcloud to go unavailable. Note: use the *availability*
    # field (online/offline), not deploy_status — validate_subcloud_status()
    # checks deploy_status and would never match "offline".
    validate_equals_with_retry(
        lambda: sc_list_kw.get_dcmanager_subcloud_list().get_subcloud_by_name(offline_subcloud).get_availability(),
        "offline",
        f"Subcloud {offline_subcloud} availability is offline",
        timeout=600,
        polling_sleep_time=15,
    )

    get_logger().log_info(f"Collect logs for subclouds {subclouds}")
    collect_output = collect_kw.collect(subcloud=subclouds)
    tar_holder["path"] = collect_output.get_tar_file_path()

    get_logger().log_info(f"Power on subcloud {offline_subcloud} and wait for online")
    power_kw.power_on()
    sc_list_kw.validate_subcloud_availability_status(offline_subcloud)

    warning_msg = f"Unreachable ; cannot collect from {offline_subcloud} (password timeout) (reason:33)"
    get_logger().log_info("Verify offline subcloud reported unreachable")
    validate_str_contains(collect_output.get_output_text(), warning_msg, f"Expected unreachable warning for {offline_subcloud}: {collect_output.get_output_text()}")

    get_logger().log_info(f"Verify available subcloud {good_subcloud} was collected")
    validate_equals(collect_output.is_name_collected(good_subcloud), True, f"Expected subcloud {good_subcloud} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_holder["path"], "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_holder["path"], [good_subcloud])


@mark.p3
@mark.lab_has_min_2_subclouds
def test_error_handling_insufficient_scratch_space(request):
    """Collect subclouds listed via ``--continue`` and verify the bundle.

    Test Steps:
        - Pick two online subclouds.
        - Write their names to /tmp/collect_continue.lst.
        - Run ``collect --subcloud all --continue``.
        - Verify the subclouds are reported collected and present in the tar.

    Teardown:
        - Remove the collected bundle and the continue list file.
    """
    central_ssh, subclouds = _pick_online_subclouds(2)
    get_logger().log_info(f"Selected subclouds for collect --continue: {subclouds}")

    get_logger().log_info(f"Create {COLLECT_CONTINUE_LIST} for subclouds {subclouds}")
    FileKeywords(central_ssh).create_file_with_echo(COLLECT_CONTINUE_LIST, " ".join(subclouds))

    collect_kw = CollectLogsKeywords(central_ssh)
    collect_output = collect_kw.collect(subcloud="all", continue_collect=True)
    tar_path = collect_output.get_tar_file_path()

    def teardown():
        _remove_bundle(central_ssh, tar_path)
        FileKeywords(central_ssh).delete_file(COLLECT_CONTINUE_LIST)

    request.addfinalizer(teardown)

    get_logger().log_info(f"Verify subclouds {subclouds} were collected")
    for name in subclouds:
        validate_equals(collect_output.is_name_collected(name), True, f"Expected subcloud {name} in collect output, got: {collect_output.get_collected_names()}")

    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, subclouds)


@mark.p3
@mark.lab_has_subcloud
def test_collect_all_logs(request):
    """Collect logs from all hosts on the (central) system and verify the bundle.

    Test Steps:
        - Run ``collect --all`` on the central controller.
        - Verify the collect output reports a bundle and the hosts are present.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    hosts = SystemHostListKeywords(central_ssh).get_system_host_list().get_host_names()
    get_logger().log_info(f"Hosts on central controller: {hosts}")

    collect_kw = CollectLogsKeywords(central_ssh)
    collect_output = collect_kw.collect(all_hosts=True)
    tar_path = collect_output.get_tar_file_path()

    request.addfinalizer(lambda: _remove_bundle(central_ssh, tar_path))

    get_logger().log_info(f"Verify collected logs in tar bundle {tar_path}")
    validate_not_none(tar_path, "collect did not report a tar bundle path")
    collect_kw.verify_collected_names_in_tar(tar_path, hosts)


@mark.p3
@mark.lab_has_subcloud
def test_invalid_password_collect_logs():
    """Collect from all hosts with a wrong password is rejected.

    Test Steps:
        - Run ``collect --all`` supplying a wrong password at the sudo prompt.
        - Verify collect reports an invalid-password error and does not proceed.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    collect_kw = CollectLogsKeywords(central_ssh)

    get_logger().log_info("Collect logs for all hosts with a wrong password")
    collect_output = collect_kw.collect(all_hosts=True, password="wrong_password", validate_rc=False)

    get_logger().log_info("Verify collect rejected the invalid password")
    validate_str_contains(collect_output.get_output_text().lower(), "invalid password", f"collect should fail with a wrong password, got: {collect_output.get_output_text()}")


@mark.p3
@mark.lab_has_subcloud
def test_error_handling_full_scratch(request):
    """Collect is refused when the controller's /scratch is over 75% used.

    Test Steps:
        - Fill /scratch on the active controller to ~77%.
        - Run ``collect --all``.
        - Verify collect refuses because /scratch usage must be below 75%.

    Teardown:
        - Remove the fill file and any collected bundle.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    collect_kw = CollectLogsKeywords(central_ssh)
    tar_holder = {}

    get_logger().log_info(f"Fill {COLLECT_BUNDLE_DIR} on the active controller to {SCRATCH_FILL_PERCENTAGE}%")
    fill_file = FileKeywords(central_ssh).fill_disk_to_percentage(COLLECT_BUNDLE_DIR, SCRATCH_FILL_PERCENTAGE)

    def teardown():
        FileKeywords(central_ssh).delete_file(fill_file)
        _remove_bundle(central_ssh, tar_holder.get("path"))

    request.addfinalizer(teardown)

    get_logger().log_info("Collect logs for all hosts with /scratch over threshold")
    collect_output = collect_kw.collect(all_hosts=True, validate_rc=False)
    tar_holder["path"] = collect_output.get_tar_file_path()

    get_logger().log_info("Verify collect refused due to insufficient /scratch space")
    output_text = collect_output.get_output_text()
    validate_str_contains(output_text, "Not enough space on remote device", f"Expected 'Not enough space on remote device' in collect output: {output_text}")
    validate_str_contains(output_text, "usage must be below 75%", f"Expected 'usage must be below 75%' in collect output: {output_text}")

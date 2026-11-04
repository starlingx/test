"""Subcloud factory restore via the GRUB Local Factory Restore option test."""

from framework.logging.automation_logger import get_logger
from keywords.bmc.ipmitool.sol.ipmitool_sol_console_keywords import IpmitoolSolConsoleKeywords
from keywords.cloud_platform.backup_restore.factory_restore_log_keywords import FactoryRestoreLogKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from pytest import mark

from config.configuration_manager import ConfigurationManager


@mark.p2
@mark.lab_has_subcloud
@mark.subcloud_lab_is_simplex
def test_subcloud_factory_restore_via_grub(request):
    """Verify subcloud factory restore via the GRUB Local Factory Restore option.

    Covers the fully-autonomous local-site factory restore: the subcloud is
    power-reset over IPMI, the "Local Factory Restore" GRUB entry is selected
    over the SOL serial console, the node runs a factory install and boots to a
    login prompt, and factory-restore completion is confirmed from the
    auto-restore log over the subcloud OAM SSH. The auto-restore log content is
    the sole authoritative pass criterion for this local flow (no DC manager is
    involved during the restore).

    Test Steps:
        - Clear any stale SOL session, then activate the console and power reset.
        - Select "Local Factory Restore" in GRUB, classifying HIT vs MISS and
          power-reset-retrying the selection on a miss (fails if the entry
          cannot be selected within the attempt budget).
        - Wait for the factory restore to boot to a login prompt.
        - Ping the subcloud OAM IP and wait until it is reachable (the node
          reaches a login prompt before its OAM is up, so SSH attempted
          immediately would time out).
        - Log in over the subcloud OAM IP via the ACE connection framework using
          the factory credentials, retrying until SSH accepts connections.
        - Wait for the restore/bootstrap ansible to complete (PLAY RECAP with
          unreachable=0 and failed=0) before verifying anything, so the
          auto-restore success marker has actually been written.
        - Source /etc/platform/openrc on the restored subcloud.
        - Wait for controller-0 to be unlocked/enabled/available.
        - Verify factory restore completion from the auto-restore log.
        - Validate subcloud health (alarms, pods, app health) after the restore.

    Teardown:
        - Deactivate the SOL console session (idempotent, always runs).
    """
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    grub_config = ConfigurationManager.get_backup_restore_config().get_factory_restore_grub_config()

    console = IpmitoolSolConsoleKeywords(subcloud_name)

    def teardown() -> None:
        """Deactivate the SOL session so the next run can activate (always runs)."""
        get_logger().log_teardown_step(f"Deactivate SOL console for {subcloud_name}")
        console.sol_deactivate()

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Clear stale SOL session for {subcloud_name}")
    console.sol_deactivate()

    get_logger().log_test_case_step(f"Activate SOL console and power reset {subcloud_name}")
    console.activate()
    console.power_reset()

    get_logger().log_test_case_step("Wait for BIOS serial console and select Local Factory Restore in GRUB (retry on miss)")
    console.boot_local_factory_restore_with_retries(grub_config.get_grub_entry_label())

    get_logger().log_test_case_step("Wait for the factory restore to reach a login prompt")
    console.wait_for_login_prompt()

    subcloud_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    oam_ip = subcloud_config.get_factory_ip()

    get_logger().log_test_case_step(f"Ping {subcloud_name} OAM {oam_ip} and wait until it is reachable")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_factory_ssh(subcloud_name)
    restore_log_keywords = FactoryRestoreLogKeywords(subcloud_ssh)
    restore_log_keywords.wait_for_oam_reachable(oam_ip)

    get_logger().log_test_case_step(f"Log in to {subcloud_name} over its OAM IP via the ACE connection framework")
    restore_log_keywords.wait_for_ssh_reachable()

    get_logger().log_test_case_step("Wait for the restore/bootstrap ansible to complete (PLAY RECAP unreachable=0, failed=0)")
    restore_log_keywords.wait_for_restore_ansible_complete()

    get_logger().log_test_case_step("Source /etc/platform/openrc on the restored subcloud")
    restore_log_keywords.source_platform_openrc()

    get_logger().log_test_case_step("Wait for controller-0 to be unlocked/enabled/available")
    restore_log_keywords.wait_for_controller_available("controller-0")

    get_logger().log_test_case_step("Verify factory restore completion from the auto-restore log (authoritative)")
    # verify_factory_restore_complete() self-asserts via validate_equals_with_retry
    # (it raises on timeout and otherwise only returns True), so no extra assertion
    # is needed here.
    restore_log_keywords.verify_factory_restore_complete()

    get_logger().log_test_case_step(f"Validate {subcloud_name} health (alarms, pods, app health) after factory restore")
    HealthKeywords(subcloud_ssh).validate_healty_cluster()

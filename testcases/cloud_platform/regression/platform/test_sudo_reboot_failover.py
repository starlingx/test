"""Tests for controller failover after a graceful ``sudo reboot``.

Validates that issuing ``sudo reboot`` on the active controller results in a
single clean failover: the peer takes over, the rebooted controller rejoins
with its uptime reset to a single boot, and no watchdog-forced crashdump /
kernel panic drives a second spontaneous reboot.

The scenario is exercised under the aggressive 100 ms heartbeat period that
originally exposed the reboot loop.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.sudo_reboot_failover_keywords import SudoRebootFailoverKeywords

DEFAULT_HEARTBEAT_PERIOD = 1000
AGGRESSIVE_HEARTBEAT_PERIOD = 100


@mark.p2
@mark.lab_has_standby_controller
def test_sudo_reboot_active_controller_clean_failover_aggressive_heartbeat(request):
    """sudo reboot yields a clean failover under a 100 ms heartbeat period.

    Test Steps:
        - Record the current heartbeat_period
        - Set heartbeat_period to 100 ms and apply
        - Gracefully reboot the active controller and wait for it to rejoin
        - Verify it rebooted exactly once and rejoined as a healthy host
        - Verify the rebooted node rejoined as standby with the peer active
        - Verify the rebooted node logged no crashdump / kernel panic

    Teardown:
        - Restore the original heartbeat_period
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    failover_keywords = SudoRebootFailoverKeywords(ssh_connection)

    original_heartbeat_period = failover_keywords.get_heartbeat_period()

    def restore_heartbeat_period():
        """Restore the heartbeat_period to its original value."""
        restore_value = original_heartbeat_period if original_heartbeat_period else DEFAULT_HEARTBEAT_PERIOD
        failover_keywords.set_heartbeat_period(int(restore_value))

    request.addfinalizer(restore_heartbeat_period)

    get_logger().log_test_case_step(f"Setting heartbeat_period to {AGGRESSIVE_HEARTBEAT_PERIOD} ms")
    failover_keywords.set_heartbeat_period(AGGRESSIVE_HEARTBEAT_PERIOD)

    get_logger().log_test_case_step("Rebooting the active controller and waiting for a single clean reboot")
    single_clean_reboot = failover_keywords.reboot_active_controller_and_wait()
    validate_equals(single_clean_reboot, True, "Active controller should reboot once and rejoin healthy")

    get_logger().log_test_case_step("Verifying the rebooted node rejoined as standby with the peer active")
    validate_equals(
        failover_keywords.rebooted_node_rejoined_as_standby(),
        True,
        "Rebooted controller should rejoin as standby with the peer holding the active role",
    )

    get_logger().log_test_case_step("Verifying no crashdump / kernel panic on the rebooted controller")
    validate_equals(
        failover_keywords.has_crashdump_or_panic(failover_keywords.get_rebooted_host_name()),
        False,
        "Rebooted controller should not have logged a crashdump or kernel panic",
    )

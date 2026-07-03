from pytest import mark

from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.dcmanager.objects.dcmanger_subcloud_list_availability_enum import DcManagerSubcloudListAvailabilityEnum
from keywords.cloud_platform.dcmanager.rehoming_utils import verify_subcloud_healthy
from keywords.cloud_platform.dcmanager.subcloud_picker_keywords import pick_subcloud_with_fallback
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords


def subcloud_swact(ssh_connection: SSHConnection) -> None:
    """Perform a swact operation between active and standby controllers on subcloud.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
    """
    system_host_list_keywords = SystemHostListKeywords(ssh_connection)
    active_controller = system_host_list_keywords.get_active_controller()
    standby_controller = system_host_list_keywords.get_standby_controller()
    get_logger().log_info(f"A 'swact' operation is about to be executed in {ssh_connection}. Current controllers' configuration before this operation: Active controller = {active_controller.get_host_name()}, Standby controller = {standby_controller.get_host_name()}.")
    system_host_swact_keywords = SystemHostSwactKeywords(ssh_connection)
    system_host_swact_keywords.host_swact()

    active_controller_after_swact = system_host_list_keywords.get_active_controller()
    standby_controller_after_swact = system_host_list_keywords.get_standby_controller()

    validate_equals(active_controller.get_id(), standby_controller_after_swact.get_id(), "Validate that active controller is now standby")
    validate_equals(standby_controller.get_id(), active_controller_after_swact.get_id(), "Validate that standby controller is now active")


@mark.p2
@mark.subcloud_lab_is_duplex
def test_swact_duplex_subcloud_c0_to_c1_and_back(request):
    """
    Verify swact in both directions on a duplex subcloud.

    This test validates that a duplex subcloud can swact from controller-0
    to controller-1 and back to controller-0 successfully, and remains
    healthy after each operation.

    If no matching subcloud is found on the primary system controller and a
    secondary system controller is configured, the test falls back to the
    secondary. This supports post-rehoming pipeline scenarios where subclouds
    may have moved to the peer cloud.

    Prerequisites:
        - A healthy duplex subcloud must be online.
        - Controller-0 must be the active controller.

    Setup:
        - Find a healthy duplex subcloud (with fallback to secondary SC)

    Test Steps:
        1. Ensure controller-0 is active on the duplex subcloud
        2. Swact from controller-0 to controller-1
        3. Validate subcloud is healthy after swact
        4. Swact from controller-1 back to controller-0
        5. Validate subcloud is healthy after swact back

    Teardown:
        - None
    """
    system_controller_ssh, result = pick_subcloud_with_fallback(
        availability=DcManagerSubcloudListAvailabilityEnum.ONLINE,
        present_in_config=True,
        lab_type=LabTypeEnum.DUPLEX,
    )

    subcloud_name = result.get_name()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    # Ensure controller-0 is active
    get_logger().log_info(f"Ensuring controller-0 is active on duplex subcloud {subcloud_name}")
    SystemHostSwactKeywords(subcloud_ssh).ensure_duplex_subcloud_c0_is_active(subcloud_name)

    # Swact from controller-0 to controller-1
    get_logger().log_info("Performing swact from controller-0 to controller-1")
    subcloud_swact(subcloud_ssh)
    verify_subcloud_healthy(system_controller_ssh, subcloud_name)

    # Swact from controller-1 back to controller-0
    get_logger().log_info("Performing swact from controller-1 back to controller-0")
    subcloud_swact(subcloud_ssh)
    verify_subcloud_healthy(system_controller_ssh, subcloud_name)

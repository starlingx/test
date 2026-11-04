"""Tests for k8sinfra systemd slice and cgroup directory structure.

Verifies the k8sinfra.slice (cgroup v2) exists with the correct
controllers delegated.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_list_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords


@mark.p2
def test_k8sinfra_slice_active() -> None:
    """Verify k8sinfra.slice is active with delegated controllers.

    Test Steps:
        - Check systemctl status of k8sinfra.slice
        - Validate slice is active
        - Read cgroup.controllers for the slice
        - Validate cpuset, cpu, io, memory, pids controllers are delegated
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Check k8sinfra.slice is active")
    is_active_keywords = SystemCTLIsActiveKeywords(ssh)
    status = is_active_keywords.is_active("k8sinfra.slice")
    validate_equals(status, "active", "k8sinfra.slice is active")

    get_logger().log_test_case_step("Validate delegated controllers")
    file_keywords = FileKeywords(ssh)
    output = file_keywords.read_file_with_sudo("/sys/fs/cgroup/k8sinfra.slice/cgroup.controllers")
    controllers = output[0].strip() if output else ""
    get_logger().log_info(f"Delegated controllers: {controllers}")

    # Match whole controller names: "cpu" is a substring of "cpuset", so a substring check
    # would pass even if only cpuset were delegated.
    delegated_controllers = controllers.split()
    for ctrl in ["cpuset", "cpu", "io", "memory", "pids"]:
        validate_list_contains(ctrl, delegated_controllers, f"k8sinfra.slice has '{ctrl}' controller")

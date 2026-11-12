"""Tests for CPU weight in systemd overrides.

Verifies CPUWeight (cgroup v2) is set correctly in systemd slice overrides.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.linux.systemctl.systemctl_show_keywords import SystemCTLShowKeywords


@mark.p2
def test_cpu_weight_in_systemd_overrides() -> None:
    """Verify CPUWeight is set in k8sinfra.slice systemd properties.

    Test Steps:
        - Query systemctl show for k8sinfra.slice CPUWeight property
        - Validate CPUWeight value is not empty or infinity
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Query CPUWeight from k8sinfra.slice")
    show_keywords = SystemCTLShowKeywords(ssh)
    value = show_keywords.get_property("k8sinfra.slice", "CPUWeight")
    get_logger().log_info(f"CPUWeight value: {value}")

    get_logger().log_test_case_step("Validate CPUWeight value is not empty or infinity")
    validate_not_equals(value, "", "CPUWeight value is not empty")
    validate_not_equals(value, "infinity", "CPUWeight is not infinity")

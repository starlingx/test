"""Tests for CPU weight/shares in systemd overrides.

Verifies CPUWeight (v2) or cpu.shares (v1) are set correctly in
systemd slice overrides.

Reference: test_isolated_cpu.py — checks kubelet args and systemd overrides.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import (
    validate_is_digit,
    validate_not_equals,
)
from keywords.cloud_platform.cgroup.cgroup_keywords import CGROUP_V1, CGROUP_V2, CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_show_keywords import SystemCTLShowKeywords


@mark.p2
def test_cpu_weight_in_systemd_overrides_v2(request: FixtureRequest) -> None:
    """Verify CPUWeight is set in k8sinfra.slice systemd properties on v2.

    Setup:
        Switch to cgroup v2 if not already active.

    Test Steps:
        - Query systemctl show for k8sinfra.slice CPUWeight property
        - Validate CPUWeight value is not empty or infinity

    Teardown:
        Revert to original cgroup version.
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)
    original = cgroup_kw.detect_cgroup_version()

    request.addfinalizer(lambda: cgroup_kw.revert_cgroup_version(original))
    cgroup_kw.switch_cgroup_version(CGROUP_V2)
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_test_case_step("Query CPUWeight from k8sinfra.slice")
    show_keywords = SystemCTLShowKeywords(ssh)
    value = show_keywords.get_property("k8sinfra.slice", "CPUWeight")
    logger.log_info(f"CPUWeight value: {value}")

    logger.log_test_case_step("Validate CPUWeight value is not empty or infinity")
    validate_not_equals(value, "", "CPUWeight value is not empty")
    validate_not_equals(value, "infinity", "CPUWeight is not infinity")


@mark.p2
def test_cpu_shares_in_cgroup_v1(request: FixtureRequest) -> None:
    """Verify cpu.shares file exists under /sys/fs/cgroup/cpu/k8sinfra/.

    Setup:
        Switch to cgroup v1 if not already active.

    Test Steps:
        - Read cpu.shares from the k8sinfra cgroup cpu controller path
        - Validate the value is numeric

    Teardown:
        Revert to original cgroup version.
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)
    original = cgroup_kw.detect_cgroup_version()

    request.addfinalizer(lambda: cgroup_kw.revert_cgroup_version(original))
    cgroup_kw.switch_cgroup_version(CGROUP_V1)
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    logger.log_test_case_step("Read cpu.shares from k8sinfra cgroup path")
    file_keywords = FileKeywords(ssh)
    output = file_keywords.read_file("/sys/fs/cgroup/cpu/k8sinfra/cpu.shares")
    result = output[0].strip() if output else ""
    logger.log_info(f"cpu.shares value: {result}")

    logger.log_test_case_step("Validate cpu.shares is numeric")
    validate_is_digit(result, "cpu.shares is a numeric value")

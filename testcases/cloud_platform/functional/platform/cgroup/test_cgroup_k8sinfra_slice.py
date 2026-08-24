"""Tests for k8sinfra systemd slice and cgroup directory structure.

Verifies the k8sinfra.slice (v2) or /sys/fs/cgroup/cpu/k8sinfra (v1)
exists with the correct controllers delegated.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.cgroup.cgroup_keywords import CGROUP_V1, CGROUP_V2, CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.systemctl.systemctl_is_active_keywords import SystemCTLIsActiveKeywords


@mark.p2
def test_k8sinfra_slice_active_v2(request: FixtureRequest) -> None:
    """Verify k8sinfra.slice is active with delegated controllers on v2.

    Setup:
        Switch to cgroup v2 if not already active.

    Test Steps:
        - Check systemctl status of k8sinfra.slice
        - Validate slice is active
        - Read cgroup.controllers for the slice
        - Validate cpuset, cpu, io, memory, pids controllers are delegated

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

    logger.log_test_case_step("Check k8sinfra.slice is active")
    is_active_keywords = SystemCTLIsActiveKeywords(ssh)
    status = is_active_keywords.is_active("k8sinfra.slice")
    validate_equals(status, "active", "k8sinfra.slice is active")

    logger.log_test_case_step("Validate delegated controllers")
    file_keywords = FileKeywords(ssh)
    output = file_keywords.read_file_with_sudo(
        "/sys/fs/cgroup/k8sinfra.slice/cgroup.controllers"
    )
    controllers = output[0].strip() if output else ""
    logger.log_info(f"Delegated controllers: {controllers}")

    for ctrl in ["cpuset", "cpu", "io", "memory", "pids"]:
        validate_str_contains(
            controllers, ctrl, f"k8sinfra.slice has '{ctrl}' controller"
        )


@mark.p2
def test_k8s_infra_cgroup_dirs_v1(request: FixtureRequest) -> None:
    """Verify /sys/fs/cgroup/cpu/k8sinfra/ directory exists on v1.

    Setup:
        Switch to cgroup v1 if not already active.

    Test Steps:
        - Check existence of the k8sinfra cgroup cpu directory
        - Validate directory exists

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

    logger.log_test_case_step("Check k8sinfra cgroup cpu directory exists")
    file_keywords = FileKeywords(ssh)
    exists = file_keywords.file_exists("/sys/fs/cgroup/cpu/k8sinfra")
    validate_equals(
        exists, True, "/sys/fs/cgroup/cpu/k8sinfra/ exists on v1"
    )

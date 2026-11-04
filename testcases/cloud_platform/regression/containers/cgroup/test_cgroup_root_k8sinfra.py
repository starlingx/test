"""Tests for cgroup root path validation.

Verifies kubelet cgroupRoot and pod cpuset paths use the correct
cgroup root (/k8sinfra, or its k8sinfra_stx.slice form on v2).
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_greater_than, validate_str_contains
from keywords.cloud_platform.cgroup.cgroup_keywords import V2_EXPECTED_VALUES, CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.grep.grep_keywords import GrepKeywords
from keywords.linux.pgrep.pgrep_keywords import PgrepKeywords


@mark.p2
def test_kubelet_cgroup_root_path() -> None:
    """Verify kubelet cgroupRoot from config.yaml is /k8sinfra.

    Test Steps:
        - Confirm the system is running cgroup v2
        - Read cgroupRoot from kubelet config.yaml
        - Validate it matches the expected cgroup root
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    cgroup_kw.validate_cgroup_v2()

    get_logger().log_test_case_step("Read cgroupRoot from kubelet config")
    grep_keywords = GrepKeywords(ssh)
    result = grep_keywords.grep_and_extract_fields("cgroupRoot", "/var/lib/kubelet/config.yaml")
    get_logger().log_info(f"kubelet cgroupRoot line: {result}")

    get_logger().log_test_case_step("Validate cgroupRoot matches expected value")
    validate_str_contains(
        result,
        V2_EXPECTED_VALUES["kubelet_cgroup_root"],
        "kubelet cgroupRoot matches expected cgroup root",
    )


@mark.p2
def test_pod_cpuset_path_contains_cgroup_root() -> None:
    """Verify kube-apiserver cpuset path contains the expected cgroup root prefix.

    The kube-apiserver image is distroless (no cat), so kubectl exec cannot be used.
    The cpuset is read from the host via /proc/<pid>/cpuset of the kube-apiserver process.

    Test Steps:
        - Confirm the system is running cgroup v2
        - Find the kube-apiserver process PID on the controller
        - Read /proc/<pid>/cpuset on the host
        - Validate cpuset path contains the expected cgroup root prefix
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    cgroup_kw.validate_cgroup_v2()

    get_logger().log_test_case_step("Find kube-apiserver process PID")
    pids = PgrepKeywords(ssh).get_pids("kube-apiserver")
    validate_greater_than(len(pids), 0, "kube-apiserver process found on controller")
    pid = pids[0]
    get_logger().log_info(f"Using kube-apiserver PID: {pid}")

    get_logger().log_test_case_step("Read /proc/<pid>/cpuset of kube-apiserver")
    cpuset_output = FileKeywords(ssh).read_file_with_sudo(f"/proc/{pid}/cpuset")
    cpuset_path = cpuset_output[0].strip() if cpuset_output else ""
    get_logger().log_info(f"kube-apiserver cpuset path: {cpuset_path}")

    get_logger().log_test_case_step("Validate cpuset contains cgroup root prefix")
    expected_prefix = V2_EXPECTED_VALUES["cgroup_root_prefix"]
    validate_str_contains(
        cpuset_path,
        expected_prefix,
        "kube-apiserver cpuset path contains cgroup root prefix",
    )

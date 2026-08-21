"""Tests for cgroup root path validation.

Verifies kubelet cgroupRoot and pod cpuset paths use the correct
cgroup root (/k8sinfra) for both cgroup v1 and v2.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.grep.grep_keywords import GrepKeywords


@mark.p2
def test_kubelet_cgroup_root_path() -> None:
    """Verify kubelet cgroupRoot from config.yaml is /k8sinfra.

    Test Steps:
        - Detect current cgroup version
        - Read cgroupRoot from kubelet config.yaml
        - Validate it matches the expected cgroup root for the version
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    logger.log_test_case_step("Detect cgroup version")
    version = cgroup_kw.detect_cgroup_version()
    expected = cgroup_kw.get_expected_values(version)
    logger.log_info(f"Detected cgroup version: {version}")

    logger.log_test_case_step("Read cgroupRoot from kubelet config")
    grep_keywords = GrepKeywords(ssh)
    result = grep_keywords.grep_and_extract_fields(
        "cgroupRoot", "/var/lib/kubelet/config.yaml"
    )
    logger.log_info(f"kubelet cgroupRoot line: {result}")

    logger.log_test_case_step("Validate cgroupRoot matches expected value")
    validate_str_contains(
        result,
        expected["kubelet_cgroup_root"],
        "kubelet cgroupRoot matches cgroup version",
    )


@mark.p2
def test_pod_cpuset_path_contains_cgroup_root() -> None:
    """Verify pod cpuset path contains the /k8sinfra/ cgroup root prefix.

    Uses kube-apiserver pod which is guaranteed to have /proc accessible.

    Test Steps:
        - Detect current cgroup version
        - Find kube-apiserver pod name using kubectl get pods
        - Read /proc/1/cpuset from the kube-apiserver container
        - Validate cpuset path contains the expected cgroup root prefix
    """
    logger = get_logger()
    ssh = LabConnectionKeywords().get_active_controller_ssh()
    cgroup_kw = CgroupKeywords(ssh)

    logger.log_test_case_step("Detect cgroup version")
    version = cgroup_kw.detect_cgroup_version()
    expected = cgroup_kw.get_expected_values(version)
    logger.log_info(f"Detected cgroup version: {version}")

    logger.log_test_case_step("Find kube-apiserver pod")
    get_pods_keywords = KubectlGetPodsKeywords(ssh)
    pods_output = get_pods_keywords.get_pods(
        namespace="kube-system", label="component=kube-apiserver"
    )
    pod_name = pods_output.get_pods_start_with("kube-apiserver")[0].get_name()
    logger.log_info(f"Using pod: {pod_name}")

    logger.log_test_case_step("Read /proc/1/cpuset from kube-apiserver")
    exec_keywords = KubectlExecInPodsKeywords(ssh)
    output = exec_keywords.run_pod_exec_cmd(
        pod_name=pod_name,
        cmd="cat /proc/1/cpuset",
        options="-n kube-system -c kube-apiserver",
    )
    cpuset_path = (
        output.strip() if isinstance(output, str) else output[0].strip()
    )
    logger.log_info(f"Pod cpuset path: {cpuset_path}")

    logger.log_test_case_step("Validate cpuset contains cgroup root prefix")
    expected_prefix = expected["cgroup_root_prefix"]
    validate_str_contains(
        cpuset_path,
        expected_prefix,
        "pod cpuset path contains cgroup root prefix",
    )

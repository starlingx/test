"""Tests for CPU and memory limits represented in the cgroup v2 hierarchy.

Deploys a pod with known CPU/memory requests and limits and verifies the
container's cgroup v2 leaf files reflect them.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_greater_than, validate_less_than_or_equal
from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.cgroup.pod_cgroup_v2_keywords import CGROUP_V2_DEFAULT_CPU_WEIGHT, CGROUP_V2_MIN_CPU_WEIGHT, PodCgroupV2Keywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_quantity_converter import K8sQuantityConverter
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

POD_NAME = "cgroup-limits-test"
POD_NAMESPACE = "default"
POD_YAML_RESOURCE = "resources/cloud_platform/containers/cgroup/cgroup_limits_test_pod.yaml"
REMOTE_POD_YAML = "/home/sysadmin/cgroup_limits_test_pod.yaml"
POD_RUNNING_TIMEOUT_SECONDS = 120

# The expected cgroup v2 values are derived from the request/limit read back from the running pod spec,
# so they cannot drift from the manifest in POD_YAML_RESOURCE.
POD_CPU_REQUEST_JSONPATH = "{.spec.containers[0].resources.requests.cpu}"
POD_CPU_LIMIT_JSONPATH = "{.spec.containers[0].resources.limits.cpu}"
POD_MEMORY_LIMIT_JSONPATH = "{.spec.containers[0].resources.limits.memory}"


@mark.p2
def test_cpu_memory_limits_in_cgroup_v2(request: FixtureRequest) -> None:
    """Verify CPU and memory limits are correctly represented in cgroups v2.

    memory.max and the cpu.max quota are compared exactly to values computed from the pod's memory and
    CPU limits. The cpu.max period is read from the file, since kubelet's cpuCFSQuotaPeriod is
    configurable. cpu.weight is only range-checked (1 < weight < 100), because the shares-to-weight
    conversion differs between OCI runtime versions. Every mapping is monotonic with 1024 shares
    (one full CPU) equal to the default weight of 100, so a sub-CPU request must land below 100.

    Setup:
        - Upload the pod YAML to the active controller
        - Apply the pod YAML and wait for the pod to reach Running status
        - Read the CPU request and the CPU and memory limits from the pod spec

    Test Steps:
        1. Confirm the system is running cgroup v2
        2. Read the cgroup v2 limits from inside the pod
        3. Verify the container's cgroup v2 cpu.weight is above the minimum and below the default
        4. Verify the container's cgroup v2 memory.max matches the memory limit
        5. Verify the container's cgroup v2 cpu.max quota matches the CPU limit for the configured period

    Teardown:
        - Delete the test pod
        - Delete the uploaded pod YAML file

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Confirm the system is running cgroup v2")
    CgroupKeywords(ssh).validate_cgroup_v2()

    def delete_pod_yaml() -> None:
        """Delete the uploaded pod YAML file."""
        get_logger().log_teardown_step("Delete uploaded pod YAML file")
        FileKeywords(ssh).delete_file(REMOTE_POD_YAML)

    def delete_pod() -> None:
        """Delete the test pod."""
        get_logger().log_teardown_step(f"Delete pod '{POD_NAME}'")
        KubectlDeletePodsKeywords(ssh).cleanup_pod(POD_NAME, POD_NAMESPACE)

    # One resource per finalizer, registered before setup. LIFO: the pod is deleted first, then the YAML file.
    request.addfinalizer(delete_pod_yaml)
    request.addfinalizer(delete_pod)

    get_logger().log_setup_step("Upload the cgroup-limits-test pod YAML")
    FileKeywords(ssh).upload_file(get_stx_resource_path(POD_YAML_RESOURCE), REMOTE_POD_YAML)

    get_logger().log_setup_step("Apply the pod YAML")
    KubectlApplyPodsKeywords(ssh).apply_from_yaml(REMOTE_POD_YAML, namespace=POD_NAMESPACE)

    get_logger().log_setup_step(f"Wait up to {POD_RUNNING_TIMEOUT_SECONDS} seconds for the pod to reach Running status")
    KubectlGetPodsKeywords(ssh).wait_for_pod_status(POD_NAME, "Running", POD_NAMESPACE, timeout=POD_RUNNING_TIMEOUT_SECONDS)

    get_logger().log_setup_step("Read the CPU request and the CPU and memory limits from the pod spec")
    jsonpath_keywords = KubectlGetPodJsonpathKeywords(ssh)
    cpu_request = jsonpath_keywords.get_pod_jsonpath_value(POD_NAME, POD_CPU_REQUEST_JSONPATH, POD_NAMESPACE)
    cpu_limit = jsonpath_keywords.get_pod_jsonpath_value(POD_NAME, POD_CPU_LIMIT_JSONPATH, POD_NAMESPACE)
    memory_limit = jsonpath_keywords.get_pod_jsonpath_value(POD_NAME, POD_MEMORY_LIMIT_JSONPATH, POD_NAMESPACE)

    get_logger().log_test_case_step("Read the cgroup v2 limits from inside the pod")
    limits = PodCgroupV2Keywords(ssh).get_pod_cgroup_v2_limits(POD_NAME, POD_NAMESPACE).get_limits()

    get_logger().log_test_case_step(f"Verify cgroup v2 cpu.weight is valid for the {cpu_request} CPU request")
    cpu_weight = limits.get_cpu_weight()
    validate_greater_than(cpu_weight, CGROUP_V2_MIN_CPU_WEIGHT, "cpu.weight is above the cgroup v2 minimum")
    validate_less_than_or_equal(cpu_weight, CGROUP_V2_DEFAULT_CPU_WEIGHT - 1, "cpu.weight is below the cgroup v2 default")

    get_logger().log_test_case_step(f"Verify cgroup v2 memory.max matches the {memory_limit} memory limit")
    converter = K8sQuantityConverter()
    validate_equals(limits.get_memory_max(), converter.memory_quantity_to_bytes(memory_limit), f"memory.max equals {memory_limit} in bytes")

    get_logger().log_test_case_step(f"Verify cgroup v2 cpu.max quota matches the {cpu_limit} CPU limit for the configured period")
    cpu_period = limits.get_cpu_period()
    validate_equals(limits.get_cpu_quota(), converter.cpu_limit_to_quota(cpu_limit, cpu_period), f"cpu.max quota equals the {cpu_limit} limit over a {cpu_period} us period")

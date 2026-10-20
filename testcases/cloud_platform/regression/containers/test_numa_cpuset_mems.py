from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import fail, validate_equals
from keywords.cloud_platform.cgroup.cgroup_keywords import CgroupKeywords
from keywords.cloud_platform.cgroup.numa_cpuset_keywords import NumaCpusetKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.sysfs.sysfs_numa_keywords import SysfsNumaKeywords

POD_NAME = "dummy-numa-test"
POD_NAMESPACE = "default"
POD_YAML_RESOURCE = "resources/cloud_platform/containers/numa_guaranteed_pod.yaml"
REMOTE_POD_YAML_PATH = "/home/sysadmin/numa_guaranteed_pod.yaml"
HOST_PLACEHOLDER = "HOST_PLACEHOLDER"

POD_RUNNING_TIMEOUT = 120


def _select_multi_numa_worker() -> str:
    """Select a worker-subfunction host that has at least two online NUMA nodes.

    Returns:
        str: The hostname of the selected multi-NUMA worker.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    workers = SystemHostListKeywords(ssh_connection).get_workers()

    for worker in workers:
        worker_host = worker.get_host_name()
        worker_ssh = LabConnectionKeywords().get_ssh_for_hostname(worker_host)
        online_node_count = SysfsNumaKeywords(worker_ssh).get_online_nodes().get_online_node_count()
        get_logger().log_info(f"{worker_host} online NUMA node count: {online_node_count}")
        if online_node_count > 1:
            return worker_host

    worker_names = [worker.get_host_name() for worker in workers]
    fail(f"No worker with more than one online NUMA node found among {worker_names}; the multi-NUMA pod scenario cannot run on this lab")


@mark.p2
@mark.lab_has_multi_numa_worker
def test_numa_cpuset_mems_guaranteed_pod_spans_all_nodes(request: FixtureRequest):
    """Verify cpuset.mems exposes all NUMA nodes for a Guaranteed pod on a multi-NUMA host.

    Test Steps:
        - Select a worker with more than one online NUMA node
        - Read the worker's online NUMA nodes and cgroup version (cpuset.mems on v1,
          cpuset.mems.effective on v2)
        - Upload the Guaranteed QoS pod definition and pin it to the worker
        - Deploy the Guaranteed pod and wait for Running
        - Verify the pod's Mems_allowed_list exposes more than one online NUMA node
        - Verify the pod's cpuset.mems exposes more than one online NUMA node
        - Verify the bare-metal k8sinfra cgroup cpuset.mems exposes all online NUMA nodes
        - Verify the bare-metal kubepods cgroup cpuset.mems exposes all online NUMA nodes

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Select a worker with more than one online NUMA node")
    worker_host = _select_multi_numa_worker()

    get_logger().log_setup_step(f"Read online NUMA nodes and cgroup version on worker {worker_host}")
    worker_ssh = LabConnectionKeywords().get_ssh_for_hostname(worker_host)
    online_nodes = SysfsNumaKeywords(worker_ssh).get_online_nodes().get_online_node_ids_as_frozenset()
    cgroup_version = CgroupKeywords(worker_ssh).detect_cgroup_version()
    get_logger().log_info(f"Worker {worker_host} online NUMA nodes {sorted(online_nodes)}; cgroup version {cgroup_version}")

    get_logger().log_setup_step(f"Upload Guaranteed pod definition and pin it to {worker_host}")
    YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file=get_stx_resource_path(POD_YAML_RESOURCE), replacement_dictionary={HOST_PLACEHOLDER: worker_host}, target_file_name="numa_guaranteed_pod.yaml", target_remote_location="/home/sysadmin")

    def cleanup_pod():
        get_logger().log_teardown_step(f"Delete pod {POD_NAME}")
        KubectlDeletePodsKeywords(LabConnectionKeywords().get_active_controller_ssh()).cleanup_pod(POD_NAME, namespace=POD_NAMESPACE)
        get_logger().log_teardown_step(f"Remove {REMOTE_POD_YAML_PATH} from controller")
        FileKeywords(ssh_connection).delete_file(REMOTE_POD_YAML_PATH)

    request.addfinalizer(cleanup_pod)

    get_logger().log_test_case_step(f"Deploy Guaranteed pod {POD_NAME} and wait for Running")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(REMOTE_POD_YAML_PATH)
    validate_equals(
        KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(POD_NAME, "Running", namespace=POD_NAMESPACE, timeout=POD_RUNNING_TIMEOUT),
        True,
        f"Pod {POD_NAME} reached Running status",
    )

    numa_cpuset_pod = NumaCpusetKeywords(ssh_connection)
    numa_cpuset_host = NumaCpusetKeywords(worker_ssh)

    get_logger().log_test_case_step("Verify pod Mems_allowed_list exposes more than one online NUMA node")
    mems_allowed_nodes = numa_cpuset_pod.get_pod_mems_allowed_nodes(POD_NAME)
    get_logger().log_info(f"Pod Mems_allowed_list nodes: {sorted(mems_allowed_nodes)}")
    validate_equals(
        len(mems_allowed_nodes) > 1 and mems_allowed_nodes.issubset(online_nodes),
        True,
        f"Pod Mems_allowed_list ({sorted(mems_allowed_nodes)}) must expose more than one online NUMA node ({sorted(online_nodes)})",
    )

    get_logger().log_test_case_step("Verify pod cpuset.mems exposes more than one online NUMA node")
    pod_cpuset_mems_nodes = numa_cpuset_pod.get_pod_cpuset_mems_nodes(POD_NAME, cgroup_version)
    get_logger().log_info(f"Pod cpuset.mems nodes: {sorted(pod_cpuset_mems_nodes)}")
    validate_equals(
        len(pod_cpuset_mems_nodes) > 1 and pod_cpuset_mems_nodes.issubset(online_nodes),
        True,
        f"Pod cpuset.mems ({sorted(pod_cpuset_mems_nodes)}) must expose more than one online NUMA node ({sorted(online_nodes)})",
    )

    get_logger().log_test_case_step("Verify bare-metal k8sinfra cgroup cpuset.mems exposes all online NUMA nodes")
    k8sinfra_nodes = numa_cpuset_host.get_k8sinfra_cpuset_mems_nodes(cgroup_version)
    get_logger().log_info(f"{worker_host} k8sinfra cpuset.mems nodes: {sorted(k8sinfra_nodes)}")
    validate_equals(
        k8sinfra_nodes,
        online_nodes,
        f"k8sinfra cgroup cpuset.mems ({sorted(k8sinfra_nodes)}) must expose all online NUMA nodes ({sorted(online_nodes)})",
    )

    get_logger().log_test_case_step("Verify bare-metal kubepods cgroup cpuset.mems exposes all online NUMA nodes")
    kubepods_nodes = numa_cpuset_host.get_kubepods_cpuset_mems_nodes(cgroup_version)
    get_logger().log_info(f"{worker_host} kubepods cpuset.mems nodes: {sorted(kubepods_nodes)}")
    validate_equals(
        kubepods_nodes,
        online_nodes,
        f"kubepods cgroup cpuset.mems ({sorted(kubepods_nodes)}) must expose all online NUMA nodes ({sorted(online_nodes)})",
    )

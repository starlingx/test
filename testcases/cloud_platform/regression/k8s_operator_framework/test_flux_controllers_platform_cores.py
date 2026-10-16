from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.crictl.crictl_inspect_keywords import CrictlInspectKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.process_status.process_status_psr_keywords import ProcessStatusPsrKeywords


@mark.p2
def test_flux_controllers_running_on_platform_cores():
    """Verify that Flux controllers run only on platform cores.

    Test Steps:
        - Get flux pods and the node each one runs on
        - For each flux pod, verify it carries the platform component label
        - For each flux pod, verify its PSR is a platform core of its node
    """
    flux_namespace = "flux-helm"
    platform_label_key = "app.starlingx.io/component"
    platform_label_value = "platform"

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()

    get_logger().log_test_case_step("Get flux pods and the node each one runs on")
    pods_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=flux_namespace)
    flux_pods = pods_output.get_pods()
    get_logger().log_info(f"Flux-helm pods: {[(pod.get_name(), pod.get_node()) for pod in flux_pods]}")

    jsonpath_keywords = KubectlGetPodJsonpathKeywords(ssh_connection)

    for pod in flux_pods:
        pod_name = pod.get_name()
        node_name = pod.get_node()
        get_logger().log_info(f"Pod {pod_name} is running on node {node_name}")

        get_logger().log_test_case_step(f"Verify pod {pod_name} has platform label")
        labels = KubectlGetPodsKeywords(ssh_connection).get_pod_labels(pod_name, namespace=flux_namespace)
        validate_equals(labels.get(platform_label_key), platform_label_value, f"Pod {pod_name} has platform component label")

        platform_log_cores = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(node_name).get_log_cores_for_assigned_function("Platform")
        get_logger().log_info(f"Platform cores on {node_name}: {platform_log_cores}")

        get_logger().log_test_case_step(f"Get container ID and PSR for {pod_name} on {node_name}")
        container_id = jsonpath_keywords.get_container_id(pod_name, namespace=flux_namespace)
        get_logger().log_info(f"Container ID: {container_id}")

        node_ssh_connection = lab_connection_keywords.get_ssh_for_hostname(node_name)
        pid = CrictlInspectKeywords(node_ssh_connection).get_container_pid(container_id)
        psr = ProcessStatusPsrKeywords(node_ssh_connection).get_psr_for_pid(pid)
        get_logger().log_info(f"Pod {pod_name} PSR: {psr}")

        validate_equals(
            psr in platform_log_cores,
            True,
            f"Pod {pod_name} PSR {psr} is assigned to a platform core on {node_name}",
        )

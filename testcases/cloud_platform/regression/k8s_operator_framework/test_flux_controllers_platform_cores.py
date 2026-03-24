from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_cpu_keywords import SystemHostCPUKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.crictl.crictl_inspect_keywords import CrictlInspectKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.process_status.process_status_psr_keywords import ProcessStatusPsrKeywords


@mark.p2
def test_flux_controllers_running_on_platform_cores():
    """
    Verify that Flux controllers run only on platform cores.

    Test Steps:
        - Get flux pod names
        - Get platform cores for active controller
        - For each flux pod, get container ID and PSR
        - Verify PSR is assigned to a platform core
    """
    flux_namespace = "flux-helm"
    platform_label_key = "app.starlingx.io/component"
    platform_label_value = "platform"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    active_controller = SystemHostListKeywords(ssh_connection).get_active_controller()
    host_name = active_controller.get_host_name()

    get_logger().log_test_case_step("Get flux pod names")
    pods_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=flux_namespace)
    pod_names = [pod.get_name() for pod in pods_output.get_pods()]
    get_logger().log_info(f"Flux-helm pods: {pod_names}")

    get_logger().log_test_case_step(f"Get platform cores for {host_name}")
    cpu_output = SystemHostCPUKeywords(ssh_connection).get_system_host_cpu_list(host_name)
    platform_cores = cpu_output.get_system_host_cpu_objects(assigned_function="Platform")
    platform_log_cores = {cpu.get_log_core() for cpu in platform_cores}
    get_logger().log_info(f"Platform cores: {platform_log_cores}")

    jsonpath_keywords = KubectlGetPodJsonpathKeywords(ssh_connection)
    crictl_keywords = CrictlInspectKeywords(ssh_connection)
    psr_keywords = ProcessStatusPsrKeywords(ssh_connection)

    for pod_name in pod_names:
        get_logger().log_test_case_step(f"Verify pod {pod_name} has platform label")
        labels = KubectlGetPodsKeywords(ssh_connection).get_pod_labels(pod_name, namespace=flux_namespace)
        validate_equals(labels.get(platform_label_key), platform_label_value, f"Pod {pod_name} has platform component label")

        get_logger().log_test_case_step(f"Get container ID and PSR for {pod_name}")
        container_id = jsonpath_keywords.get_container_id(pod_name, namespace=flux_namespace)
        get_logger().log_info(f"Container ID: {container_id}")

        pid = crictl_keywords.get_container_pid(container_id)
        psr = psr_keywords.get_psr_for_pid(pid)
        get_logger().log_info(f"Pod {pod_name} PSR: {psr}")

        validate_equals(
            psr in platform_log_cores,
            True,
            f"Pod {pod_name} PSR {psr} is assigned to a platform core",
        )
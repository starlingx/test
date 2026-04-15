from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.kubernetes_version_list_keywords import SystemKubernetesListKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

# Mapping of k8s version to expected snapshot-controller image tag
VERSION_COMPARISON_LIST = {
    "1.24": "snapshot-controller:v4.0.0",
    "1.25": "snapshot-controller:v4.2.1",
    "1.26": "snapshot-controller:v6.1.0",
    "1.27": "snapshot-controller:v6.1.0",
    "1.28": "snapshot-controller:v6.1.0",
    "1.29": "snapshot-controller:v6.1.0",
    "1.30": "snapshot-controller:v6.3.3",
    "1.31": "snapshot-controller:v8.0.0",
    "1.32": "snapshot-controller:v8.0.0",
    "1.33": "snapshot-controller:v8.1.0",
    "1.34": "snapshot-controller:v8.1.0",
    "1.35": "snapshot-controller:v8.1.0",
}


@mark.p3
def test_check_kube_version_comparing_with_snapshot_controller():
    """
    Test to check if the kube version matches the proper volume snapshot controller

    Test Steps:
        - Grab Kube version
        - Grab volume snapshot controller version
        - Compare them and return if they match
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Get kube version")
    kube_version_list = SystemKubernetesListKeywords(ssh_connection).get_system_kube_version_list()
    k8s_version = kube_version_list.get_active_kubernetes_version()
    get_logger().log_info(f"Active Kubernetes version: {k8s_version}")

    get_logger().log_test_case_step("Get Volume Snapshot controller version")
    pods_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace="kube-system", label="app=volume-snapshot-controller")
    volume_snapshot_pod = pods_output.get_pods()[0].get_name()

    # Get the container image using jsonpath
    jsonpath_keywords = KubectlGetPodJsonpathKeywords(ssh_connection)
    image_value = jsonpath_keywords.get_pod_jsonpath_value(
        pod_name=volume_snapshot_pod,
        jsonpath="{.spec.containers[0].image}",
        namespace="kube-system",
    )
    # Extract the image tag after the last '/' (e.g. "snapshot-controller:v8.0.0")
    volume_snapshot_pod_version = image_value[image_value.rindex("/") + 1 :].strip()
    get_logger().log_info(f"Volume snapshot controller version: {volume_snapshot_pod_version}")

    get_logger().log_test_case_step(f"Check whether k8s version:{k8s_version} matching with " f"volume_snapshot version:{volume_snapshot_pod_version}")
    for k8s_ver, expected_snapshot_ver in VERSION_COMPARISON_LIST.items():
        if k8s_ver in k8s_version:
            validate_equals(volume_snapshot_pod_version, expected_snapshot_ver, "Comparing the versions.")
            return

    raise ValueError(f"k8s version:{k8s_version} is not in the list. The TC needs to be updated.")

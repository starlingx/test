"""PVC Pod Setup and Teardown — Availability Test Pods Helm Chart.

Deploys and removes the availability-test-pods Helm chart.
Run test_setup_pvc_pod to deploy, test_teardown_pvc_pod to clean up.

Prerequisites:
- Lab is accessible and active controller is available
- Storage backend (ceph or netapp) is configured
- availability-test-pods-0.2.0.tgz is present in resources

Run with:
    python framework/runner/scripts/test_executor.py \
        --tests_location=testcases/cloud_platform/system_test/test_setup_pvc_pod.py::test_setup_pvc_pod \
        --lab_config_file=config/lab/files/<lab>.json5

    python framework/runner/scripts/test_executor.py \
        --tests_location=testcases/cloud_platform/system_test/test_setup_pvc_pod.py::test_teardown_pvc_pod \
        --lab_config_file=config/lab/files/<lab>.json5
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from keywords.cloud_platform.helm.helm_release_keywords import HelmReleaseKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords


REMOTE_PATH = "/home/sysadmin"
CHART_RESOURCE_PATH = "resources/cloud_platform/storage/pvc_pod/availability-test-pods-0.2.0.tgz"
CHART_FILENAME = "availability-test-pods-0.2.0.tgz"
RELEASE_NAME = "availability-test-pods"
RELEASE_NAMESPACE = "test-pods"
POD_NAME_PREFIXES = ["availability-test-service", "availability-test-service-with-pvc"]


@mark.p0
def test_setup_pvc_pod() -> None:
    """Deploy availability-test-pods Helm chart and verify pod status.

    Deploys the availability-test-pods Helm chart via helm upgrade --install
    and verifies that the PVCs are bound and pods reach Running status.
    Pods are left running for use by subsequent tests.

    Preconditions:
        - Lab is accessible
        - Storage backend is configured and healthy

    Setup:
        - Establish SSH connection to active controller
        - Upload Helm chart to controller

    Test Steps:
        1. Install availability-test-pods Helm chart
        2. Verify PVCs reach Bound status
        3. Verify pods reach Running status

    Teardown:
        - None (pods left running for subsequent tests)
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_setup_step("Upload Helm chart to controller")
    local_chart_path = get_stx_resource_path(CHART_RESOURCE_PATH)
    remote_chart_path = f"{REMOTE_PATH}/{CHART_FILENAME}"
    FileKeywords(ssh_connection).upload_file(local_chart_path, remote_chart_path, overwrite=True)

    get_logger().log_test_case_step("Install availability-test-pods Helm chart")
    HelmReleaseKeywords(ssh_connection).helm_upgrade_install(
        RELEASE_NAME, remote_chart_path, RELEASE_NAMESPACE, create_namespace=True
    )

    get_logger().log_test_case_step("Verify PVCs reach Bound status")
    KubectlGetPvcKeywords(ssh_connection).wait_for_pvcs_to_reach_status(
        expected_status="Bound", namespace=RELEASE_NAMESPACE
    )

    get_logger().log_test_case_step("Verify pods reach Running status")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status(
        expected_status="Running", pod_names=POD_NAME_PREFIXES, namespace=RELEASE_NAMESPACE
    )


@mark.p0
def test_teardown_pvc_pod() -> None:
    """Uninstall availability-test-pods Helm release and clean up.

    Removes the availability-test-pods Helm release from the test-pods namespace,
    which deletes all pods, deployments, and PVCs created by the chart.

    Preconditions:
        - availability-test-pods Helm release is deployed

    Setup:
        - Establish SSH connection to active controller

    Test Steps:
        1. Uninstall the availability-test-pods Helm release
        2. Verify pods are fully terminated
        3. Remove the uploaded chart file from the controller

    Teardown:
        - None
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Uninstall the availability-test-pods Helm release")
    HelmReleaseKeywords(ssh_connection).helm_uninstall(RELEASE_NAME, RELEASE_NAMESPACE)

    get_logger().log_test_case_step("Verify pods are fully terminated")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_be_deleted(namespace=RELEASE_NAMESPACE)

    get_logger().log_test_case_step("Remove the uploaded chart file from the controller")
    FileKeywords(ssh_connection).delete_file(f"{REMOTE_PATH}/{CHART_FILENAME}")

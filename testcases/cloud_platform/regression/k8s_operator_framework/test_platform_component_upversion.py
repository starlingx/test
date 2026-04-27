import re
import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.helm.helm_release_keywords import HelmReleaseKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.clusterrole.kubectl_describe_clusterrole_keywords import KubectlDescribeClusterroleKeywords
from keywords.k8s.helm.kubectl_delete_helm_release_keywords import KubectlDeleteHelmReleaseKeywords
from keywords.k8s.helm.kubectl_get_helm_release_keywords import KubectlGetHelmReleaseKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pod_jsonpath_keywords import KubectlGetPodJsonpathKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_pod_logs_keywords import KubectlPodLogsKeywords

HELM_APP_NAME = "hello-kitty"
HELM_APP_FILE = "hello-kitty-min-k8s-version.tgz"


@mark.p3
@mark.lab_has_ceph
def test_kubectl_delete_helm_release(request: FixtureRequest):
    """
    Verify that if helm release is deleted the helm release does not come back
    """
    namespace = "kube-system"
    helm_release_name = "rbd-provisioner"

    # Step 1: Get helm release to delete
    get_logger().log_test_case_step("Get helm release to delete")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    helm_releases_list = KubectlGetHelmReleaseKeywords(ssh_connection).get_helm_releases_by_namespace(namespace=namespace)
    validate_equals(helm_releases_list.is_helm_release(helm_release_name), True, f"Helm release {helm_release_name} not found on {namespace} namespace")

    # Step 2: Delete helm release
    get_logger().log_test_case_step("Delete helm release")
    KubectlDeleteHelmReleaseKeywords(ssh_connection).delete_helm_release(namespace=namespace, helm_name=helm_release_name)

    def teardown():
        # Step 4: Clean up the test environment by deleting the created resources (teardown).
        get_logger().log_test_case_step(f"Reapplying platform-integ-apps to reinstall {helm_release_name}.")
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply("platform-integ-apps")

    request.addfinalizer(teardown)

    # Step 3: Confirm that the helm release is cleaned up and not come back
    get_logger().log_test_case_step("Confirm that the helm release is cleaned up and does not come back after 3 minutes")
    KubectlGetHelmReleaseKeywords(ssh_connection).validate_helm_release_exists(False, helm_name=helm_release_name, namespace=namespace, validation_description="The helm release was removed")
    get_logger().log_info("We need to make sure that the release doesn't come back after 3 minutes. Sleeping for 3 minutes")
    time.sleep(180)
    KubectlGetHelmReleaseKeywords(ssh_connection).validate_helm_release_exists(False, helm_name=helm_release_name, namespace=namespace, validation_description="The helm release didn't come back")


@mark.p3
def test_verify_clusterrolebindings():
    """
    Verify cluster role bindings on the lab.

    Test Steps:
        - kubectl describe clusterrole crd-controller -n flux-helm
        - Verify the resources and verbs are as expected
    """
    expected_resource_and_verbs = {
        "*.image.toolkit.fluxcd.io": "[*]",
        "namespaces": "[get list watch]",
        "secrets": "[get list watch]",
        "serviceaccounts": "[get list watch]",
        "configmaps": "[get list watch create update patch delete]",
        "leases.coordination.k8s.io": "[get list watch create update patch delete]",
        "configmaps/status": "[get update patch]",
    }

    # Step 1: Get the clusterrole description
    get_logger().log_test_case_step("Describe clusterrole crd-controller in flux-helm namespace")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    clusterrole_output = KubectlDescribeClusterroleKeywords(ssh_connection).describe_clusterrole(
        clusterrole_name="crd-controller",
        namespace="flux-helm",
    )

    # Step 2: Verify expected resources and verbs
    get_logger().log_test_case_step("Verify expected resources and verbs in cluster role bindings")
    for resource, expected_verbs in expected_resource_and_verbs.items():
        has_match = clusterrole_output.has_resource_with_verbs(resource, expected_verbs)
        validate_equals(has_match, True, f"Resource '{resource}' has expected verbs '{expected_verbs}'")


@mark.p3
def test_flux_pods_running_on_controllers():
    """
    Verify that flux-helm pod tolerations match the controller labels.

    Test Steps:
        - Get flux pod names in flux-helm namespace
        - For each flux-helm pod, get the tolerations via jsonpath
        - Verify that the pod tolerations match the expected controller tolerations
    """
    flux_namespace = "flux-helm"
    expected_tolerations = {
        "node-role.kubernetes.io/master",
        "node-role.kubernetes.io/control-plane",
        "node.kubernetes.io/not-ready",
        "node.kubernetes.io/unreachable",
    }

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Step 1: Get flux pod names
    get_logger().log_test_case_step("Get flux-helm pod names")
    pods_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=flux_namespace)
    flux_pods = pods_output.get_pods()
    get_logger().log_info(f"Found {len(flux_pods)} flux-helm pods")

    # Step 2: Verify tolerations for each pod
    jsonpath_keywords = KubectlGetPodJsonpathKeywords(ssh_connection)
    toleration_jsonpath = '{range .spec.tolerations[*]}{.key}{"\\n"}{end}'

    for pod in flux_pods:
        pod_name = pod.get_name()
        get_logger().log_test_case_step(f"Get tolerations for pod {pod_name} and compare with controller labels")
        tolerations_output = jsonpath_keywords.get_pod_jsonpath_value(pod_name, toleration_jsonpath, namespace=flux_namespace)
        actual_tolerations = {t for t in tolerations_output.strip().splitlines() if t}

        validate_equals(
            actual_tolerations,
            expected_tolerations,
            f"Pod {pod_name} tolerations match expected controller tolerations",
        )


@mark.p3
def test_delete_helm_and_source_pods(request: FixtureRequest):
    """
    Verify that helm and source controller pods are recreated successfully post-deletion.

    Test Steps:
        - Get flux-helm pods and verify they are running
        - Delete all flux-helm pods
        - Verify pods get recreated and are healthy
        - Check new pod logs for errors
        - Verify no new alarms
        - Upload and apply hello-kitty app to confirm flux is functional
    """
    flux_namespace = "flux-helm"
    healthy_statuses = ["Running", "Succeeded", "Completed"]

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Step 1: Get flux pods and verify they are running
    get_logger().log_test_case_step("Get flux-helm pods and verify they are running")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods_output = pods_keywords.get_pods(namespace=flux_namespace)
    flux_pods = pods_output.get_pods()
    get_logger().log_info(f"Flux-helm pods: {[p.get_name() for p in flux_pods]}")

    is_healthy = pods_keywords.wait_for_all_pods_status(healthy_statuses, timeout=300)
    validate_equals(is_healthy, True, "All pods are healthy before deletion")

    # Capture alarms before the test
    pre_alarms = AlarmListKeywords(ssh_connection).alarm_list()

    # Step 2: Delete all flux-helm pods
    get_logger().log_test_case_step("Delete all flux-helm pods")
    delete_keywords = KubectlDeletePodsKeywords(ssh_connection)
    for pod in flux_pods:
        delete_keywords.delete_pod(pod.get_name(), namespace=flux_namespace)

    # Verify pods get recreated and are healthy
    get_logger().log_test_case_step("Verify flux-helm pods get recreated and are healthy")
    is_healthy = pods_keywords.wait_for_pods_to_reach_status(expected_status=healthy_statuses, namespace=flux_namespace, timeout=300)
    validate_equals(is_healthy, True, "All flux-helm pods are healthy after recreation")

    # Get new pod names and check logs for errors
    get_logger().log_test_case_step("Check new pod logs for errors")
    new_pods = pods_keywords.get_pods(namespace=flux_namespace).get_pods()
    get_logger().log_info(f"New flux-helm pods: {[p.get_name() for p in new_pods]}")

    logs_keywords = KubectlPodLogsKeywords(ssh_connection)
    for pod in new_pods:
        pod_name = pod.get_name()
        pod_logs = logs_keywords.get_pod_logs(pod_name, namespace=flux_namespace)
        log_text = "\n".join(pod_logs) if isinstance(pod_logs, list) else str(pod_logs)
        error_match = re.search(r"(ERROR)", log_text)
        validate_equals(error_match, None, f"No ERROR found in logs for pod {pod_name}")

    # Step 5: Verify no new alarms
    get_logger().log_test_case_step("Verify no new alarms")
    post_alarms = AlarmListKeywords(ssh_connection).alarm_list()
    validate_equals(post_alarms, pre_alarms, "No new alarms after pod deletion and recreation")

    # Teardown: remove and delete hello-kitty app if it was applied
    def teardown():
        get_logger().log_test_case_step("Teardown: Remove and delete hello-kitty app if present")
        SystemApplicationRemoveKeywords(ssh_connection).cleanup_app_if_present(HELM_APP_NAME, force_removal=True, force_deletion=True)

    request.addfinalizer(teardown)

    # Upload and apply hello-kitty app to confirm flux is functional
    get_logger().log_test_case_step("Upload and apply hello-kitty app")
    local_path = get_stx_resource_path(f"resources/cloud_platform/containers/{HELM_APP_FILE}")
    admin_user = ConfigurationManager.get_lab_config().get_admin_credentials().get_user_name()
    remote_path = f"/home/{admin_user}/{HELM_APP_FILE}"

    FileKeywords(ssh_connection).upload_file(local_file_path=local_path, remote_file_path=remote_path)

    SystemApplicationUploadKeywords(ssh_connection).system_application_upload_and_apply_app(HELM_APP_NAME, remote_path)


@mark.p3
@mark.lab_has_ceph
def test_delete_helm_stx_rbd_provisioner_release():
    """
    Verify that a helm release comes back after manually deleting it via helm uninstall.

    Test Steps:
        - Verify platform-integ-apps is applied
        - Run helm ls -A and verify stx-rbd-provisioner appears
        - Uninstall stx-rbd-provisioner via helm uninstall
        - Verify stx-rbd-provisioner is recreated automatically
    """
    stx_provisioner = "stx-rbd-provisioner"
    namespace = "kube-system"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Step 1: Verify platform-integ-apps is applied
    get_logger().log_test_case_step("Verify platform-integ-apps is applied")
    app_show = SystemApplicationShowKeywords(ssh_connection).get_system_application_show("platform-integ-apps")
    app_status = app_show.get_system_application_object().get_status()
    get_logger().log_info(f"platform-integ-apps status is {app_status}")
    validate_equals(app_status, "applied", "platform-integ-apps is applied")

    # Step 2: Verify stx-rbd-provisioner exists
    get_logger().log_test_case_step(f"Verify {stx_provisioner} helm release exists")
    helm_keywords = HelmReleaseKeywords(ssh_connection)
    helm_keywords.wait_for_release_present(stx_provisioner, namespace=namespace)

    # Step 3: Uninstall stx-rbd-provisioner
    get_logger().log_test_case_step(f"Uninstall {stx_provisioner}")
    helm_keywords.helm_uninstall(stx_provisioner, namespace=namespace)

    # Step 4: Verify stx-rbd-provisioner is recreated
    get_logger().log_test_case_step(f"Verify {stx_provisioner} is recreated automatically")
    helm_keywords.wait_for_release_present(stx_provisioner, namespace=namespace)

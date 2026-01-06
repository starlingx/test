import time

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.k8s.helm.kubectl_delete_helm_release_keywords import KubectlDeleteHelmReleaseKeywords
from keywords.k8s.helm.kubectl_get_helm_release_keywords import KubectlGetHelmReleaseKeywords


@mark.p3
@mark.lab_ceph
def test_kubectl_delete_helm_release(request: FixtureRequest):
    """
    Verify that if helm release is deleted the helm release does not come back
    """
    namespace = "kube-system"
    helm_release_name = "rbd-provisioner"

    # Step 1: Get helm release to delete
    get_logger().log_test_case_step("Step 1: Get helm release to delete")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    helm_releases_list = KubectlGetHelmReleaseKeywords(ssh_connection).get_helm_releases_by_namespace(namespace=namespace)
    validate_equals(helm_releases_list.is_helm_release(helm_release_name), True, f"Helm release {helm_release_name} not found on {namespace} namespace")

    # Step 2: Delete helm release
    get_logger().log_test_case_step("Step 2: Delete helm release")
    KubectlDeleteHelmReleaseKeywords(ssh_connection).delete_helm_release(namespace=namespace, helm_name=helm_release_name)

    def teardown():
        # Step 4: Clean up the test environment by deleting the created resources (teardown).
        get_logger().log_test_case_step(f"Step 4: Reapplying platform-integ-apps to reinstall {helm_release_name}.")
        SystemApplicationApplyKeywords(ssh_connection).system_application_apply("platform-integ-apps")

    request.addfinalizer(teardown)

    # Step 3: Confirm that the helm release is cleaned up and not come back
    get_logger().log_test_case_step("Step 3: Confirm that the helm release is cleaned up and does not come back after 3 minutes")
    KubectlGetHelmReleaseKeywords(ssh_connection).validate_helm_release_exists(False, helm_name=helm_release_name, namespace=namespace, validation_description="The helm release was removed")
    get_logger().log_info("We need to make sure that the release doesn't come back after 3 minutes. Sleeping for 3 minutes")
    time.sleep(180)
    KubectlGetHelmReleaseKeywords(ssh_connection).validate_helm_release_exists(False, helm_name=helm_release_name, namespace=namespace, validation_description="The helm release didn't come back")

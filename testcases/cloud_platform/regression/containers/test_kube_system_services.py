from pytest import mark

from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.deployments.kubectl_get_deployments_keywords import KubectlGetDeploymentsKeywords
from keywords.k8s.pods.validation.kubectl_get_pods_validation_keywords import KubectlPodValidationKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords

KUBESYSTEM_NAMESPACE = "kube-system"


@mark.p0
def test_kube_system_services_active():
    """
    Test kube-system pods are deployed and running on active controller.

    Test Steps:
        - SSH to active controller
        - Check all kube-system pods are running
        - Check kube-system services displayed: 'kube-dns'
        - Check kube-system deployments displayed: 'calico-kube-controllers', 'coredns'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Check kube-system pods status on active controller")
    KubectlPodValidationKeywords(ssh_connection).validate_kube_system_pods_status()

    get_logger().log_test_case_step("Check kube-system service: kube-dns")
    kubectl_get_service_keywords = KubectlGetServiceKeywords(ssh_connection)
    kubectl_get_service_keywords.get_service(service_name="kube-dns", namespace=KUBESYSTEM_NAMESPACE)

    get_logger().log_test_case_step("Check kube-system deployments: calico-kube-controllers, coredns")
    kubectl_get_deployments_keywords = KubectlGetDeploymentsKeywords(ssh_connection)
    kubectl_get_deployments_keywords.get_deployment(deployment_name="calico-kube-controllers", namespace=KUBESYSTEM_NAMESPACE)
    kubectl_get_deployments_keywords.get_deployment(deployment_name="coredns", namespace=KUBESYSTEM_NAMESPACE)


@mark.p1
@mark.lab_has_standby_controller
def test_kube_system_services_standby():
    """
    Test kube-system pods are deployed and running on standby controller.

    Test Steps:
        - SSH to standby controller
        - Check all kube-system pods are running
        - Check kube-system services displayed: 'kube-dns'
        - Check kube-system deployments displayed: 'calico-kube-controllers', 'coredns'
    """
    ssh_connection = LabConnectionKeywords().get_standby_controller_ssh()

    get_logger().log_test_case_step("Check kube-system pods status on standby controller")
    KubectlPodValidationKeywords(ssh_connection).validate_kube_system_pods_status()

    get_logger().log_test_case_step("Check kube-system service: kube-dns")
    kubectl_get_service_keywords = KubectlGetServiceKeywords(ssh_connection)
    kubectl_get_service_keywords.get_service(service_name="kube-dns", namespace=KUBESYSTEM_NAMESPACE)

    get_logger().log_test_case_step("Check kube-system deployments: calico-kube-controllers, coredns")
    kubectl_get_deployments_keywords = KubectlGetDeploymentsKeywords(ssh_connection)
    kubectl_get_deployments_keywords.get_deployment(deployment_name="calico-kube-controllers", namespace=KUBESYSTEM_NAMESPACE)
    kubectl_get_deployments_keywords.get_deployment(deployment_name="coredns", namespace=KUBESYSTEM_NAMESPACE)

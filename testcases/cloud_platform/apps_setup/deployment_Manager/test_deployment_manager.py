from config.configuration_manager import ConfigurationManager
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.k8s.crd.kubectl_hosts_keywords import KubectlHostsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords


def test_validate_dm_app_applied():
    """
    Validate deployment manager application is applied

    Raises:
        Exception: If application application is not applied
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    deployment_manager_name = app_config.get_deployment_manager_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Verifies if the app is present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(deployment_manager_name), True, f"The {deployment_manager_name} application should be already applied on the system")


def test_validate_hosts_reconciled_state():
    """
    Validate all hosts are in reconciled state

    Raises:
        Exception: If any host is not in reconciled state
    """

    lab_connect_keywords = LabConnectionKeywords()
    namespace = "deployment"
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    host_output = KubectlHostsKeywords(ssh_connection).get_hosts(namespace=namespace)

    for host in host_output.kubectl_hosts_objects:
        validate_equals(host.reconcile, "true", f"Host {host.name} should be reconciled")
        validate_equals(host.insync, "true", f"Host {host.name} should be insync")


def test_platform_deployment_manager_pod_running_state():
    """
    Validate deployment manager and dm monitor pod is in running state

    Raises:
        Exception: If deployment manager pod is not in running state
    """

    # Setups app configs and lab connection
    lab_connect_keywords = LabConnectionKeywords()
    namespace = "platform-deployment-manager"
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    pod_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=namespace)
    for pod in pod_output.kubectl_pod:
        validate_equals(pod.status, "Running", f"Pod {pod.name} should be in Running state")


def test_helm_override_deployment_manager_app():
    """
    Validate deployment manager application is updated successfully

    Raises:
        Exception: If application application is not updated successfully
    """

    # Setups app configs and lab connection
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    helm_keywords = SystemHelmOverrideKeywords(ssh_connection)

    # Updated helm override value for the deployment manager application

    helm_keywords.update_helm_override_via_set("conf.cloud-platform-deployment-manager.DEFAULT.DEBUG=true", "deployment-manager", "cloud-platform-deployment-manager", "platform-deployment-manager")
    helm_keywords.get_system_helm_override_show("deployment-manager", "cloud-platform-deployment-manager", "platform-deployment-manager")
    helm_keywords.verify_helm_user_override("DEBUG: true", "deployment-manager", "cloud-platform-deployment-manager", "platform-deployment-manager")

    # Delete the helm override value for the deployment manager application
    helm_keywords.delete_system_helm_override("deployment-manager", "cloud-platform-deployment-manager", "platform-deployment-manager")
    helm_keywords.get_system_helm_override_show("deployment-manager", "cloud-platform-deployment-manager", "platform-deployment-manager")
    helm_keywords.get_system_helm_override_show("deployment-manager", "cloud-platform-deployment-manager", "platform-deployment-manager")


def test_remove_deployment_manager_app():
    """
    Validate deployment manager application is removed successfully

    Raises:
        Exception: If application application is not removed successfully
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    deployment_manager_name = app_config.get_deployment_manager_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    namespace = "platform-deployment-manager"

    # Verifies if the app is present in the system
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    validate_equals(system_applications.is_in_application_list(deployment_manager_name), True, f"The {deployment_manager_name} application should be uploaded/applied on the system")

    # Verifies if the app is removed from the system
    # Removes the application
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(deployment_manager_name)
    system_application_remove_input.set_force_removal(False)
    system_application_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(system_application_remove_input)
    validate_equals(system_application_output.get_system_application_object().get_status(), SystemApplicationStatusEnum.UPLOADED.value, "Application removal status validation")
    pod_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=namespace)
    for pod in pod_output.kubectl_pod:
        validate_not_equals(pod.status, "Running", f"Pod {pod.name} should not be in Running state after application removal")

    # Deletes the application
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(deployment_manager_name)
    system_application_delete_input.set_force_deletion(False)
    delete_msg = SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_equals(delete_msg, f"Application {deployment_manager_name} deleted.\n", "Application deletion message validation")


def test_reapply_deployment_manager_app():
    """
    Validate deployment manager application is removed successfully

    Raises:
        Exception: If application application is not removed successfully
    """

    # Setups app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    deployment_manager_name = app_config.get_deployment_manager_app_name()
    base_path = app_config.get_base_application_path()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()
    namespace = "platform-deployment-manager"

    # Verifies if the app is already uploaded
    system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(deployment_manager_name):
        deployment_manager_app_status = system_applications.get_application(deployment_manager_name).get_status()
        validate_equals(deployment_manager_app_status, "uploaded", f"{deployment_manager_name} is already uploaded")
    else:
        # Setups the upload input object
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(deployment_manager_name)
        system_application_upload_input.set_tar_file_path(f"{base_path}{deployment_manager_name}*.tgz")
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(system_application_upload_input)
        system_applications = SystemApplicationListKeywords(ssh_connection).get_system_application_list()
        deployment_manager_app_status = system_applications.get_application(deployment_manager_name).get_status()
        validate_equals(deployment_manager_app_status, "uploaded", f"{deployment_manager_name} upload status validation")
    # Applies the app to the active controller
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(deployment_manager_name)

    # Verifies the app was applied
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), deployment_manager_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")
    pod_output = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=namespace)
    for pod in pod_output.kubectl_pod:
        validate_equals(pod.status, "Running", f"Pod {pod.name} should be in Running state after application removal")

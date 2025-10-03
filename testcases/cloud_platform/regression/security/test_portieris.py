from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.docker.objects.registry import Registry
from config.security.objects.security_config import SecurityConfig
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_keywords import SystemHelmKeywords
from keywords.docker.trust.docker_trust_keywords import DockerTrustKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.imagepolicy.kubectl_delete_imagepolicy_keywords import KubectlDeleteImagePolicyKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "portieris"
CHART_PATH = "/usr/local/share/applications/helm/portieris-[0-9]*"
NAMESPACE = "pvtest"


def setup_portieris_environment(ssh_connection: SSHConnection, security_config: SecurityConfig) -> None:
    """Setup Portieris application and test environment.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        security_config (SecurityConfig): Security configuration object.
    """
    # Setup Portieris if not present
    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if not system_app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Uploading {APP_NAME} application")
        ls_keywords = LsKeywords(ssh_connection)
        actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
        upload_input = SystemApplicationUploadInput()
        upload_input.set_tar_file_path(actual_chart)
        upload_input.set_app_name(APP_NAME)
        system_app_upload = SystemApplicationUploadKeywords(ssh_connection)
        system_app_upload.system_application_upload(upload_input)

    # Setup helm overrides and apply application
    system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
    if not system_app_apply.is_already_applied(APP_NAME):
        get_logger().log_info(f"Setting up {APP_NAME} helm overrides for caCert")
        helm_keywords = SystemHelmKeywords(ssh_connection)
        yaml_keywords = YamlKeywords(ssh_connection)
        template_file = get_stx_resource_path("resources/cloud_platform/security/portieris/caCert.yaml")
        replacement_dict = {"registry_ca_cert": security_config.get_portieris_registry_ca_cert()}
        portieris_overrides = yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, "caCert.yaml", "/tmp")
        helm_keywords.helm_override_update(APP_NAME, "portieris", "portieris", portieris_overrides)

        get_logger().log_info(f"Applying {APP_NAME} application")
        system_app_apply.system_application_apply(APP_NAME)

    # Wait for Portieris pods
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    pods_output = kubectl_pods.get_pods("portieris")
    running_pods = pods_output.get_pods_with_status("Running")
    validate_equals(len(running_pods) > 0, True, "At least one Portieris pod should be running")

    # Create namespace and registry secret
    kubectl_create_ns = KubectlCreateNamespacesKeywords(ssh_connection)
    kubectl_create_ns.create_namespaces(NAMESPACE)
    registry_hostname = security_config.get_portieris_registry_hostname()
    username = security_config.get_portieris_registry_username()
    password = security_config.get_portieris_registry_password()
    registry = Registry("registry", registry_hostname, username, password)
    kubectl_create_secret = KubectlCreateSecretsKeywords(ssh_connection)
    kubectl_create_secret.create_secret_for_registry(registry, "registry-secret", NAMESPACE)


def cleanup_portieris_environment(ssh_connection: SSHConnection) -> None:
    """Clean up Portieris test resources.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
    """
    get_logger().log_info("Cleaning up Portieris test resources")

    kubectl_delete_ns = KubectlDeleteNamespaceKeywords(ssh_connection)
    kubectl_delete_ns.cleanup_namespace(NAMESPACE)

    kubectl_delete_policies = KubectlDeleteImagePolicyKeywords(ssh_connection)
    kubectl_delete_policies.delete_all_clusterimagepolicies()
    kubectl_delete_policies.delete_all_imagepolicies()

    system_app_list = SystemApplicationListKeywords(ssh_connection)
    if system_app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Removing {APP_NAME} application")
        system_app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if system_app_apply.is_already_applied(APP_NAME):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(APP_NAME)
            system_app_remove = SystemApplicationRemoveKeywords(ssh_connection)
            system_app_remove.system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(APP_NAME)
        delete_input.set_force_deletion(True)
        system_app_delete = SystemApplicationDeleteKeywords(ssh_connection)
        system_app_delete.get_system_application_delete(delete_input)


@mark.p1
def test_portieris_image_security_policy(request):
    """Test Portieris image security with image policy.

    Steps:
        - Setup Portieris application and test environment
        - Apply image policy configuration
        - Test unsigned image deployment (should be rejected)
        - Validate signed image signatures
        - Test signed image deployment (should be accepted)
    """
    get_logger().log_info("Starting Portieris image security test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    def cleanup():
        cleanup_portieris_environment(ssh_connection)

    request.addfinalizer(cleanup)

    setup_portieris_environment(ssh_connection, security_config)

    # Initialize keyword classes directly in test
    yaml_keywords = YamlKeywords(ssh_connection)
    kubectl_file_apply = KubectlFileApplyKeywords(ssh_connection)
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    docker_trust = DockerTrustKeywords(ssh_connection)

    # Apply image policy
    policy_template = get_stx_resource_path("resources/cloud_platform/security/portieris/image-policy.yaml")
    registry_hostname = security_config.get_portieris_registry_hostname()
    registry_port = security_config.get_portieris_registry_port()
    replacement_dict = {"registry_server": registry_hostname, "registry_port": registry_port, "signed_repo": "wrcp-test-signed", "trust_server": security_config.get_portieris_trust_server(), "namespace": NAMESPACE}
    policy_file = yaml_keywords.generate_yaml_file_from_template(policy_template, replacement_dict, "image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(policy_file)

    # Test unsigned image (should be rejected)
    get_logger().log_info("Testing unsigned image deployment (should be rejected)")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "unsigned_image_name": security_config.get_portieris_unsigned_image_name()}
    pod_file = yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-policy.yaml", "/tmp")

    # Use kubectl_apply_with_error and validate in test case
    error_output = kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = ssh_connection.get_return_code()
    validate_not_equals(return_code, 0, "kubectl apply should fail for policy rejection")
    validate_str_contains(error_output, "trust.hooks.securityenforcement.admission.cloud.ibm.com", "Output should contain Portieris admission webhook")

    # Validate signatures using docker trust keywords
    get_logger().log_info("Verifying signed image has valid signatures")
    signed_image = security_config.get_portieris_signed_image_name()
    trust_server = security_config.get_portieris_trust_server()
    trust_output = docker_trust.inspect_docker_trust(signed_image, trust_server)
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    # Test signed image (should be accepted)
    get_logger().log_info("Testing signed image deployment (should be accepted)")
    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running")


@mark.p1
def test_portieris_cluster_image_policy(request):
    """Test Portieris image security with cluster image policy.

    Steps:
        - Setup Portieris application and test environment
        - Apply cluster image policy configuration
        - Test unsigned image deployment (should be rejected)
        - Validate signed image signatures
        - Test signed image deployment (should be accepted)
    """
    get_logger().log_info("Starting Portieris cluster image policy test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    def cleanup():
        cleanup_portieris_environment(ssh_connection)

    request.addfinalizer(cleanup)

    setup_portieris_environment(ssh_connection, security_config)

    # Initialize keyword classes directly in test
    yaml_keywords = YamlKeywords(ssh_connection)
    kubectl_file_apply = KubectlFileApplyKeywords(ssh_connection)
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    docker_trust = DockerTrustKeywords(ssh_connection)

    # Apply cluster image policy
    policy_template = get_stx_resource_path("resources/cloud_platform/security/portieris/cluster-image-policy.yaml")
    registry_hostname = security_config.get_portieris_registry_hostname()
    registry_port = security_config.get_portieris_registry_port()
    replacement_dict = {"registry_server": registry_hostname, "registry_port": registry_port, "signed_repo": "wrcp-test-signed", "trust_server": security_config.get_portieris_trust_server(), "namespace": NAMESPACE}
    policy_file = yaml_keywords.generate_yaml_file_from_template(policy_template, replacement_dict, "cluster-image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(policy_file)

    # Test unsigned image (should be rejected)
    get_logger().log_info("Testing unsigned image deployment (should be rejected)")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "unsigned_image_name": security_config.get_portieris_unsigned_image_name()}
    pod_file = yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-cluster-image-policy.yaml", "/tmp")

    # Use kubectl_apply_with_error and validate in test case
    error_output = kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = ssh_connection.get_return_code()
    validate_not_equals(return_code, 0, "kubectl apply should fail for policy rejection")
    validate_str_contains(error_output, "trust.hooks.securityenforcement.admission.cloud.ibm.com", "Output should contain Portieris admission webhook")

    # Validate signatures using docker trust keywords
    get_logger().log_info("Verifying signed image has valid signatures")
    signed_image = security_config.get_portieris_signed_image_name()
    trust_server = security_config.get_portieris_trust_server()
    trust_output = docker_trust.inspect_docker_trust(signed_image, trust_server)
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    # Test signed image (should be accepted)
    get_logger().log_info("Testing signed image deployment (should be accepted)")
    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-cluster-image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running")

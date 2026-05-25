import time

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
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.docker.trust.docker_trust_keywords import DockerTrustKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.imagepolicy.kubectl_delete_imagepolicy_keywords import KubectlDeleteImagePolicyKeywords
from keywords.k8s.k8s_base_keyword import K8sBaseKeyword
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "portieris"
CHART_PATH = "/usr/local/share/applications/helm/portieris-[0-9]*"
NAMESPACE = "pvtest"


def wait_for_portieris_webhook_ready(ssh_connection: SSHConnection, timeout: int = 180) -> None:
    """Wait for the Portieris admission webhook service to have ready endpoints.

    After a reboot or swact, the webhook endpoint may appear before it is fully
    responsive. This function waits for the endpoint to exist and then allows
    additional settle time for the webhook to become fully operational.

    Args:
        ssh_connection (SSHConnection): SSH connection to active controller.
        timeout (int): Maximum seconds to wait for endpoint readiness.
    """
    k8s = K8sBaseKeyword(ssh_connection)
    deadline = time.time() + timeout
    while time.time() < deadline:
        output = ssh_connection.send(k8s.k8s_config.export("kubectl get endpoints portieris -n portieris -o jsonpath='{.subsets[0].addresses[0].ip}'"))
        content = "\n".join(output) if isinstance(output, list) else str(output)
        if content.strip() and "error" not in content.lower():
            get_logger().log_info(f"Portieris webhook endpoint ready: {content.strip()}")
            get_logger().log_info("Waiting 40s for webhook to become fully responsive")
            time.sleep(40)
            return
        get_logger().log_info("Portieris webhook endpoint not ready yet, retrying...")
        time.sleep(10)
    get_logger().log_info("Portieris webhook readiness wait timed out, proceeding")


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

    # Verify portieris-certs certificate is issued by cert-manager
    get_logger().log_info("Verifying portieris-certs certificate is Ready")
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    cert_keywords.wait_for_certs_status("portieris-certs", True, namespace="portieris", timeout=120)

    # Wait for Portieris admission webhook to be reachable
    get_logger().log_info("Waiting for Portieris admission webhook to be ready")
    wait_for_portieris_webhook_ready(ssh_connection)

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
    trust_output = docker_trust.inspect_docker_trust(security_config.get_portieris_signed_image_name(), security_config.get_portieris_trust_server())
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
@mark.lab_has_standby_controller
def test_portieris_image_security_before_after_swact(request):
    """Test Portieris image policy enforcement survives controller swact.

    Steps:
        - Setup Portieris application and test environment
        - Apply image policy configuration
        - Verify unsigned image rejected and signed image accepted
        - Perform controller swact
        - Verify unsigned image rejected and signed image accepted after swact
    """
    get_logger().log_info("Starting Portieris swact resilience test (ImagePolicy)")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    def cleanup():
        cleanup_ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_portieris_environment(cleanup_ssh)

    request.addfinalizer(cleanup)

    setup_portieris_environment(ssh_connection, security_config)

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

    # Verify BEFORE swact: unsigned rejected
    get_logger().log_info("Verifying policy enforcement BEFORE swact")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "unsigned_image_name": security_config.get_portieris_unsigned_image_name()}
    pod_file = yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-policy.yaml", "/tmp")
    error_output = kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = ssh_connection.get_return_code()
    validate_not_equals(return_code, 0, "kubectl apply should fail for unsigned image")
    validate_str_contains(error_output, "trust.hooks.securityenforcement.admission.cloud.ibm.com", "Output should contain Portieris admission webhook")

    # Verify BEFORE swact: signed accepted
    trust_output = docker_trust.inspect_docker_trust(security_config.get_portieris_signed_image_name(), security_config.get_portieris_trust_server())
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running before swact")

    # Perform swact
    get_logger().log_info("Performing controller swact")
    swact_success = SystemHostSwactKeywords(ssh_connection).host_swact()
    validate_equals(swact_success, True, "Controller swact should complete successfully")

    # Reconnect to new active controller
    new_ssh = LabConnectionKeywords().get_active_controller_ssh()
    new_kubectl_pods = KubectlGetPodsKeywords(new_ssh)
    new_kubectl_file_apply = KubectlFileApplyKeywords(new_ssh)
    new_yaml_keywords = YamlKeywords(new_ssh)

    # Wait for portieris pods after swact
    portieris_pods = new_kubectl_pods.get_pods("portieris")
    running_pods = portieris_pods.get_pods_with_status("Running")
    validate_equals(len(running_pods) > 0, True, "Portieris pods should be running after swact")

    # Cleanup pre-swact test pod
    KubectlDeletePodsKeywords(new_ssh).cleanup_pod("test-pod", NAMESPACE)

    # Verify AFTER swact: unsigned rejected
    get_logger().log_info("Verifying policy enforcement AFTER swact")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "unsigned_image_name": security_config.get_portieris_unsigned_image_name()}
    pod_file = new_yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-post-swact.yaml", "/tmp")
    error_output = new_kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = new_ssh.get_return_code()
    validate_not_equals(return_code, 0, "kubectl apply should fail for unsigned image after swact")

    # Verify AFTER swact: signed accepted
    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = new_yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-post-swact.yaml", "/tmp")
    new_kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = new_kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running after swact")


@mark.p2
@mark.lab_has_standby_controller
def test_portieris_image_security_before_after_reboot(request):
    """Test Portieris image policy enforcement survives controller reboot.

    Steps:
        - Setup Portieris application and test environment
        - Apply image policy configuration
        - Verify unsigned image rejected and signed image accepted
        - Verify standby controller is available
        - Reboot the active controller (ungraceful, triggers automatic swact)
        - Reconnect to new active controller
        - Wait for rebooted controller to come back online
        - Verify unsigned image rejected and signed image accepted after reboot
    """
    get_logger().log_info("Starting Portieris reboot resilience test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    def cleanup():
        cleanup_ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_portieris_environment(cleanup_ssh)

    request.addfinalizer(cleanup)

    setup_portieris_environment(ssh_connection, security_config)

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

    # Verify BEFORE reboot: unsigned rejected
    get_logger().log_info("Verifying policy enforcement BEFORE reboot")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "unsigned_image_name": security_config.get_portieris_unsigned_image_name()}
    pod_file = yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-pre-reboot.yaml", "/tmp")
    error_output = kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = ssh_connection.get_return_code()
    validate_not_equals(return_code, 0, "kubectl apply should fail for unsigned image")
    validate_str_contains(error_output, "trust.hooks.securityenforcement.admission.cloud.ibm.com", "Output should contain Portieris admission webhook")

    # Verify BEFORE reboot: signed accepted
    trust_output = docker_trust.inspect_docker_trust(security_config.get_portieris_signed_image_name(), security_config.get_portieris_trust_server())
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-pre-reboot.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running before reboot")

    # Cleanup test pod before reboot
    KubectlDeletePodsKeywords(ssh_connection).cleanup_pod("test-pod", NAMESPACE)

    # Verify standby controller is available before rebooting active
    get_logger().log_info("Verifying standby controller is available")
    host_list_keywords = SystemHostListKeywords(ssh_connection)
    standby_controller = host_list_keywords.get_standby_controller()
    standby_hostname = standby_controller.get_host_name()
    validate_equals(standby_controller.get_availability(), "available", f"Standby controller {standby_hostname} should be available before reboot")

    # Ungraceful reboot of active controller — triggers automatic swact to standby
    active_controller = host_list_keywords.get_active_controller()
    active_hostname = active_controller.get_host_name()
    get_logger().log_info(f"Force rebooting active controller: {active_hostname}")
    reboot_keywords = SystemHostRebootKeywords(ssh_connection)
    reboot_keywords.host_force_reboot()

    # Reconnect to new active controller (standby took over)
    get_logger().log_info("Reconnecting to new active controller after reboot")
    new_ssh = LabConnectionKeywords().get_active_controller_ssh()

    # Wait for the rebooted controller to come back online naturally
    get_logger().log_info(f"Waiting for {active_hostname} to come back online")
    lock_keywords = SystemHostLockKeywords(new_ssh)
    host_back = lock_keywords.wait_for_host_unlocked(active_hostname, unlock_wait_timeout=1200)
    validate_equals(host_back, True, f"{active_hostname} should come back online after reboot")

    # Wait for portieris pods to stabilize and webhook to be ready
    get_logger().log_info("Waiting for Portieris pods and webhook to stabilize after reboot")
    new_kubectl_pods = KubectlGetPodsKeywords(new_ssh)
    new_kubectl_pods.wait_for_pods_to_reach_status("Running", namespace="portieris", timeout=300)
    cert_keywords = KubectlGetCertStatusKeywords(new_ssh)
    cert_keywords.wait_for_certs_status("portieris-certs", True, namespace="portieris", timeout=120)
    wait_for_portieris_webhook_ready(new_ssh)

    # Verify AFTER reboot: unsigned rejected
    get_logger().log_info("Verifying policy enforcement AFTER reboot")
    new_yaml_keywords = YamlKeywords(new_ssh)
    new_kubectl_file_apply = KubectlFileApplyKeywords(new_ssh)
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "unsigned_image_name": security_config.get_portieris_unsigned_image_name()}
    pod_file = new_yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-post-reboot.yaml", "/tmp")
    error_output = new_kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = new_ssh.get_return_code()
    validate_not_equals(return_code, 0, "kubectl apply should fail for unsigned image after reboot")

    # Verify AFTER reboot: signed accepted
    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = new_yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-post-reboot.yaml", "/tmp")
    new_kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = new_kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running after reboot")

    get_logger().log_info("Portieris image policy enforcement survived reboot successfully")


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
    trust_output = docker_trust.inspect_docker_trust(security_config.get_portieris_signed_image_name(), security_config.get_portieris_trust_server())
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    # Test signed image (should be accepted)
    get_logger().log_info("Testing signed image deployment (should be accepted)")
    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {"namespace": NAMESPACE, "test_pod_name": "test-pod", "signed_image_name": security_config.get_portieris_signed_image_name(), "pull_secret_name": "registry-secret"}
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-cluster-image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running")

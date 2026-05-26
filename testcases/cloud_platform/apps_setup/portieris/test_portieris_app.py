from pytest import mark

from config.configuration_manager import ConfigurationManager
from config.docker.objects.registry import Registry
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_keywords import SystemHelmKeywords
from keywords.docker.trust.docker_trust_keywords import DockerTrustKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "portieris"
CHART_PATH = "/usr/local/share/applications/helm/portieris-[0-9]*"
NAMESPACE = "pvtest"


@mark.p1
@mark.lab_is_simplex
def test_portieris_pre_upgrade():
    """Verify portieris is applied and policy enforcement works before upgrade.

    Runs before both platform upgrades and kubernetes upgrades to establish
    that portieris is functional. Leaves the application applied so the
    upgrade proceeds with portieris in place.

    Test Steps:
        - Check if portieris application is present
        - Upload and apply portieris if not present
        - Verify portieris pods are running
        - Apply image policy and verify unsigned image is rejected
        - Verify signed image is accepted
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    # Ensure portieris is uploaded and applied
    get_logger().log_test_case_step("Ensure portieris application is applied")
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    if not app_list_keywords.is_app_present(APP_NAME):
        get_logger().log_info(f"Uploading {APP_NAME} application")
        ls_keywords = LsKeywords(ssh_connection)
        actual_chart = ls_keywords.get_first_matching_file(CHART_PATH)
        upload_input = SystemApplicationUploadInput()
        upload_input.set_tar_file_path(actual_chart)
        upload_input.set_app_name(APP_NAME)
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    if not app_apply.is_already_applied(APP_NAME):
        get_logger().log_info(f"Setting up {APP_NAME} helm overrides for caCert")
        helm_keywords = SystemHelmKeywords(ssh_connection)
        yaml_keywords = YamlKeywords(ssh_connection)
        template_file = get_stx_resource_path("resources/cloud_platform/security/portieris/caCert.yaml")
        replacement_dict = {"registry_ca_cert": security_config.get_portieris_registry_ca_cert()}
        portieris_overrides = yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dict, "caCert.yaml", "/tmp")
        helm_keywords.helm_override_update(APP_NAME, "portieris", "portieris", portieris_overrides)
        get_logger().log_info(f"Applying {APP_NAME} application")
        app_apply.system_application_apply(APP_NAME)

    # Verify pods are running
    get_logger().log_test_case_step("Verify portieris pods are running")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    pods_output = kubectl_pods.get_pods("portieris")
    running_pods = pods_output.get_pods_with_status("Running")
    validate_equals(len(running_pods) > 0, True, "At least one portieris pod should be running before upgrade")

    # Verify policy enforcement
    get_logger().log_test_case_step("Verify policy enforcement before upgrade")
    yaml_keywords = YamlKeywords(ssh_connection)
    kubectl_file_apply = KubectlFileApplyKeywords(ssh_connection)
    docker_trust = DockerTrustKeywords(ssh_connection)

    kubectl_create_ns = KubectlCreateNamespacesKeywords(ssh_connection)
    kubectl_create_ns.create_namespaces(NAMESPACE)
    registry_hostname = security_config.get_portieris_registry_hostname()
    username = security_config.get_portieris_registry_username()
    password = security_config.get_portieris_registry_password()
    registry = Registry("registry", registry_hostname, username, password)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(registry, "registry-secret", NAMESPACE)

    policy_template = get_stx_resource_path("resources/cloud_platform/security/portieris/image-policy.yaml")
    registry_port = security_config.get_portieris_registry_port()
    replacement_dict = {
        "registry_server": registry_hostname,
        "registry_port": registry_port,
        "signed_repo": "wrcp-test-signed",
        "trust_server": security_config.get_portieris_trust_server(),
        "namespace": NAMESPACE,
    }
    policy_file = yaml_keywords.generate_yaml_file_from_template(policy_template, replacement_dict, "image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(policy_file)

    # Unsigned image should be rejected
    get_logger().log_test_case_step("Verify unsigned image is rejected")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {
        "namespace": NAMESPACE,
        "test_pod_name": "test-pod",
        "unsigned_image_name": security_config.get_portieris_unsigned_image_name(),
    }
    pod_file = yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-pre-upgrade.yaml", "/tmp")
    error_output = kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = ssh_connection.get_return_code()
    validate_not_equals(return_code, 0, "Unsigned image should be rejected by portieris policy")
    validate_str_contains(
        error_output,
        "trust.hooks.securityenforcement.admission.cloud.ibm.com",
        "Output should contain Portieris admission webhook",
    )

    # Signed image should be accepted
    get_logger().log_test_case_step("Verify signed image is accepted")
    trust_output = docker_trust.inspect_docker_trust(
        security_config.get_portieris_signed_image_name(),
        security_config.get_portieris_trust_server(),
    )
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {
        "namespace": NAMESPACE,
        "test_pod_name": "test-pod",
        "signed_image_name": security_config.get_portieris_signed_image_name(),
        "pull_secret_name": "registry-secret",
    }
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-pre-upgrade.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running before upgrade")

    get_logger().log_info("Portieris pre-upgrade validation complete — app left applied for upgrade")


@mark.p1
@mark.lab_is_simplex
def test_portieris_post_upgrade():
    """Verify portieris survived upgrade: app applied, pods running, policy enforced.

    Runs after both platform upgrades and kubernetes upgrades to confirm
    portieris is still functional.

    Test Steps:
        - Validate portieris application is present and in applied state
        - Verify portieris pods are running
        - Apply image policy and verify unsigned image is rejected
        - Verify signed image is accepted
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()

    # Validate app is still applied after upgrade
    get_logger().log_test_case_step("Validate portieris app is still applied after upgrade")
    app_list = SystemApplicationListKeywords(ssh_connection)
    validate_equals(app_list.is_app_present(APP_NAME), True, "Portieris should be present after upgrade")
    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    validate_equals(app_apply.is_already_applied(APP_NAME), True, "Portieris should be applied after upgrade")

    # Verify pods are running
    get_logger().log_test_case_step("Verify portieris pods are running after upgrade")
    kubectl_pods = KubectlGetPodsKeywords(ssh_connection)
    pods_output = kubectl_pods.get_pods("portieris")
    running_pods = pods_output.get_pods_with_status("Running")
    validate_equals(len(running_pods) > 0, True, "At least one portieris pod should be running after upgrade")

    # Verify policy enforcement after upgrade
    get_logger().log_test_case_step("Verify policy enforcement after upgrade")
    yaml_keywords = YamlKeywords(ssh_connection)
    kubectl_file_apply = KubectlFileApplyKeywords(ssh_connection)
    docker_trust = DockerTrustKeywords(ssh_connection)

    kubectl_create_ns = KubectlCreateNamespacesKeywords(ssh_connection)
    kubectl_create_ns.create_namespaces(NAMESPACE)
    registry_hostname = security_config.get_portieris_registry_hostname()
    username = security_config.get_portieris_registry_username()
    password = security_config.get_portieris_registry_password()
    registry = Registry("registry", registry_hostname, username, password)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_for_registry(registry, "registry-secret", NAMESPACE)

    policy_template = get_stx_resource_path("resources/cloud_platform/security/portieris/image-policy.yaml")
    registry_port = security_config.get_portieris_registry_port()
    replacement_dict = {
        "registry_server": registry_hostname,
        "registry_port": registry_port,
        "signed_repo": "wrcp-test-signed",
        "trust_server": security_config.get_portieris_trust_server(),
        "namespace": NAMESPACE,
    }
    policy_file = yaml_keywords.generate_yaml_file_from_template(policy_template, replacement_dict, "image-policy.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(policy_file)

    # Unsigned image should be rejected
    get_logger().log_test_case_step("Verify unsigned image is rejected after upgrade")
    unsigned_template = get_stx_resource_path("resources/cloud_platform/security/portieris/unsigned-image.yaml")
    replacement_dict = {
        "namespace": NAMESPACE,
        "test_pod_name": "test-pod",
        "unsigned_image_name": security_config.get_portieris_unsigned_image_name(),
    }
    pod_file = yaml_keywords.generate_yaml_file_from_template(unsigned_template, replacement_dict, "unsigned-image-post-upgrade.yaml", "/tmp")
    error_output = kubectl_file_apply.kubectl_apply_with_error(pod_file)
    return_code = ssh_connection.get_return_code()
    validate_not_equals(return_code, 0, "Unsigned image should be rejected after upgrade")
    validate_str_contains(
        error_output,
        "trust.hooks.securityenforcement.admission.cloud.ibm.com",
        "Output should contain Portieris admission webhook after upgrade",
    )

    # Signed image should be accepted
    get_logger().log_test_case_step("Verify signed image is accepted after upgrade")
    trust_output = docker_trust.inspect_docker_trust(
        security_config.get_portieris_signed_image_name(),
        security_config.get_portieris_trust_server(),
    )
    validate_str_contains(trust_output, "Signers", "Signed image should have valid signatures")

    signed_template = get_stx_resource_path("resources/cloud_platform/security/portieris/signed-image.yaml")
    replacement_dict = {
        "namespace": NAMESPACE,
        "test_pod_name": "test-pod",
        "signed_image_name": security_config.get_portieris_signed_image_name(),
        "pull_secret_name": "registry-secret",
    }
    pod_file = yaml_keywords.generate_yaml_file_from_template(signed_template, replacement_dict, "signed-image-post-upgrade.yaml", "/tmp")
    kubectl_file_apply.apply_resource_from_yaml(pod_file)
    pod_running = kubectl_pods.wait_for_pod_status("test-pod", "Running", NAMESPACE, 300)
    validate_equals(pod_running, True, "Signed image pod should be running after upgrade")

    get_logger().log_info("Portieris post-upgrade validation complete — app functional after upgrade")

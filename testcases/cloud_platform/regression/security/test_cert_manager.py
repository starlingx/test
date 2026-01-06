from pytest import FixtureRequest, mark

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains, validate_str_contains, validate_str_contains_with_retry
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.certificate.kubectl_get_issuer_keywords import KubectlGetCertIssuerKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords


@mark.p3
def test_override_cert_manager():
    """
    Verify post-install override functionality of cert-manager app.

    Test Steps:
        - Override helm values using system override
        - Re-apply the application
        - Confirm pods are in Running state post-override

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    app_name = "cert-manager"
    chart_name = "cert-manager"
    namespace = "cert-manager"
    label_key = "test"
    label_value = "cm_label"
    label = f"{label_key}: {label_value}"
    k8s_label = f"{label_key}={label_value}"

    cm_override_file_name = "cm_override_values.yaml"

    config_file_locations = ConfigurationFileLocationsManager()
    ConfigurationManager.load_configs(config_file_locations)

    template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{cm_override_file_name}")
    replacement_dictionary = {"cm_label_key": label_key, "cm_label_value": label_value}
    get_logger().log_info(f"Creating resource from file {template_file}")
    remote_path = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, f"{cm_override_file_name}", "/home/sysadmin")

    get_logger().log_info(f"Helm override for {app_name} with custom values")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_path, app_name, chart_name, namespace)

    get_logger().log_info(f"Verify helm override show for {app_name} with custom values")
    SystemHelmOverrideKeywords(ssh_connection).verify_helm_user_override(label, app_name, chart_name, namespace)
    get_logger().log_info(f"Re-apply the {app_name} application")
    # Step 3: Re-apply the cert manager app on the active controller

    # Executes the application installation
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)

    # Asserts that the applying process concluded successfully
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_str_contains(system_application_object.get_name(), app_name, "Apply cert-manager")
    validate_str_contains(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Apply cert-manager")

    def get_pod_status():
        pod_status = KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=namespace, label=k8s_label).get_pods_start_with(app_name)[0].get_status()
        return pod_status == "Running"

    validate_equals_with_retry(get_pod_status, True, 600)


@mark.p3
def test_manual_cert_installation(request: FixtureRequest):
    """
    Test manual installation of 'system-registry-local-certificate', 'system-restapi-gui-certificate'

    Args:
        request (FixtureRequest): request needed for adding teardown

    Steps:
        - Create the namespace
        - Deploy the Stepca issuer
        - Install the stepca root secret
        - Deploy the cert with stepca issuer
        - Verify that installed cert shown in "system certificate-list"
        - Now deploy a certificate
        - Check that the manual installation of certificate is accepted
    Teardown:
        - Delete the namespace

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()

    cluster_issuer = "system-selfsigning-issuer"
    root_ca_cert = "cloudplatform-rootca-certificate"
    root_ca_secret = "cloudplatform-rootca-secret"
    platform_issuer = "cloudplatform-issuer"
    registry_local_cert = "system-registry-local-certificate"
    registry_local_secret = "system-registry-local-secret"
    restapi_gui_cert = "system-restapi-gui-certificate"
    restapi_gui_secret = "system-restapi-gui-secret"

    registry_local_cert_file_name = "registry_local_cert.yaml"
    restapi_gui_cert_file_name = "restapi_gui_cert.yaml"
    cluster_issuer_file_name = "cluster_issuer.yaml"
    root_cacert_file_name = "root_ca_cert.yaml"
    platform_issuer_file_name = "platform_issuer.yaml"
    namespace = "testcert"

    kubectl_create_ns_keyword = KubectlCreateNamespacesKeywords(ssh_connection)
    kubectl_create_ns_keyword.create_namespaces(namespace)
    ns_list = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces()

    validate_equals(ns_list.is_namespace(namespace_name=namespace), True, "create namespace")

    cluster_issuer_template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{cluster_issuer_file_name}")
    issuer_replacement_dictionary = {"cluster_issuer": cluster_issuer}
    cluster_issuer_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(cluster_issuer_template_file, issuer_replacement_dictionary, f"{cluster_issuer_file_name}", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(cluster_issuer_yaml)

    root_cacert_template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{root_cacert_file_name}")
    root_cacert_replacement_dictionary = {"root_ca_cert": root_ca_cert, "root_ca_secret": root_ca_secret, "cluster_issuer": cluster_issuer, "namespace": namespace}
    root_cacert_issuer_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(root_cacert_template_file, root_cacert_replacement_dictionary, f"{root_cacert_file_name}", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(root_cacert_issuer_yaml)
    platform_issuer_template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{platform_issuer_file_name}")
    platform_issuer_replacement_dictionary = {"root_ca_secret": root_ca_secret, "platform_issuer": platform_issuer, "namespace": namespace}
    platform_issuer_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(platform_issuer_template_file, platform_issuer_replacement_dictionary, f"{platform_issuer_file_name}", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(platform_issuer_yaml)

    KubectlGetCertIssuerKeywords(ssh_connection).wait_for_issuer_status(platform_issuer, True, namespace)
    # Check the cert status
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(root_ca_cert, True, namespace)
    root_ca_list_of_secrets = KubectlGetSecretsKeywords(ssh_connection).get_secret_names(namespace=namespace)
    validate_list_contains(root_ca_secret, root_ca_list_of_secrets, "Root ca secret")
    KubectlGetCertIssuerKeywords(ssh_connection).wait_for_issuer_status(platform_issuer, True, namespace)

    registry_local_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{registry_local_cert_file_name}")
    registry_replacement_dictionary = {"registry_local_cert": registry_local_cert, "registry_local_secret": registry_local_secret, "platform_issuer": platform_issuer, "floating_ip": oam_ip, "namespace": namespace}
    registry_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(registry_local_file, registry_replacement_dictionary, f"{registry_local_cert_file_name}", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(registry_yaml)
    # Check the cert status
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(registry_local_cert, True, namespace)

    def get_list_of_secrets():
        return KubectlGetSecretsKeywords(ssh_connection).get_secret_names(namespace=namespace)

    validate_str_contains_with_retry(get_list_of_secrets, registry_local_secret, "Registry local secret", timeout=10)
    restapi_gui_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{restapi_gui_cert_file_name}")
    restapi_replacement_dictionary = {"restapi_gui_cert": restapi_gui_cert, "restapi_gui_secret": restapi_gui_secret, "platform_issuer": platform_issuer, "floating_ip": oam_ip, "namespace": namespace}
    restapi_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(restapi_gui_file, restapi_replacement_dictionary, f"{restapi_gui_cert_file_name}", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(restapi_yaml)
    # Check the cert status
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(restapi_gui_cert, True, namespace)
    validate_str_contains_with_retry(get_list_of_secrets, restapi_gui_secret, "restapi gui secret", timeout=10)

    def teardown_namespace():
        # cleanup created dashboard namespace
        get_logger().log_info("Deleting testcert namespace")
        ns_list = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces()

        if ns_list.is_namespace(namespace_name=namespace):
            get_logger().log_info("Deleting testcert namespace")
            # delete created namespace
            KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace=namespace)
        else:
            get_logger().log_info("testcert namespace does not exist")

    request.addfinalizer(teardown_namespace)

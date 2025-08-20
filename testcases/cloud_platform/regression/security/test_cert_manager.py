from pytest import FixtureRequest, mark

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains, validate_str_contains, validate_str_contains_with_retry
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.ssh.lab_info_keywords import LabInfoKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.certificate.kubectl_get_issuer_keywords import KubectlGetCertIssuerKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.network.ip_address_keywords import IPAddressKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


@mark.p0
def test_app_using_nginx_controller(request):
    """
    This test is to deploy an application which uses Nginx Ingress controller using a
    certificate signed by External CA(acme stepCA)

    Steps:
        - Deploy and apply the app file
        - Deploy and apply the globalnetworkpolicy for the acme challenge
        - Verify app status
        - Verify cert is issued from StepCa
        - Check the app url

    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    dns_name = LabInfoKeywords().get_fully_qualified_name()
    dns_resolution_status = IPAddressKeywords(oam_ip).check_dnsname_resolution(dns_name=dns_name)
    validate_equals(dns_resolution_status, True, "Verify the dns name resolution")
    stepca_url = ConfigurationManager.get_security_config().get_stepca_server_url()
    stepca_issuer = "stepca-issuer"
    pod_name = "kuard"
    cert = "kuard-ingress-tls"
    base_url = f"https://{dns_name}/"
    deploy_app_file_name = "deploy_app.yaml"
    global_policy_file_name = "global_policy.yaml"
    kuard_file_name = "kuard.yaml"
    namespace = "pvtest"
    tls_secret_name = "kuard-ingress-tls"

    file_keywords = FileKeywords(ssh_connection)
    secret_json_keywords = KubectlGetSecretsKeywords(ssh_connection)

    # Upload and apply global policy
    global_policy_remote_path = f"/home/sysadmin/{global_policy_file_name}"
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{global_policy_file_name}"), global_policy_remote_path, overwrite=False)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(f"/home/sysadmin/{global_policy_file_name}")

    # Upload and render deploy app file
    template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{deploy_app_file_name}")
    replacement_dictionary = {"stepca_server_url": stepca_url}
    deploy_app_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, deploy_app_file_name, "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(deploy_app_yaml)

    # Check the issuer status
    KubectlGetCertIssuerKeywords(ssh_connection).wait_for_issuer_status(stepca_issuer, True, namespace)
    # Check the ingress pod status
    get_pod_obj = KubectlGetPodsKeywords(ssh_connection)
    pod_name = get_pod_obj.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_name)

    pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_pod_status(pod_name, "Running", namespace)
    validate_equals(pod_status, True, "Verify ingress pods are running")

    template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{kuard_file_name}")
    replacement_dictionary = {"dns_name": dns_name}
    nginx_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, f"{kuard_file_name}", "/home/sysadmin")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(nginx_yaml)
    # Check the cert status
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(cert, True, namespace)
    # Check the app url
    response = CloudRestClient().get(f"{base_url}")
    validate_equals(response.get_status_code(), 200, "Verify the app url is reachable")

    # Verify cert is issued from StepCa
    issuer = secret_json_keywords.get_certificate_issuer(tls_secret_name, namespace)
    expected_issuer = ConfigurationManager.get_security_config().get_stepca_server_issuer()
    validate_equals(issuer, expected_issuer, f"Verify the certificate issuer is '{expected_issuer}'")

    def teardown():
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)
        KubectlFileDeleteKeywords(ssh_connection).delete_resources(global_policy_remote_path)

    request.addfinalizer(teardown)


@mark.p0
def test_simple_ingress_routing_http(request):
    """
    This test verifies ingress routing using path-based rules for HTTP.

    Steps:
        - Apply simple ingress routing resources (pods, services, ingress)
        - Validate /apple and /banana routes respond correctly
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    namespace = "pvtest"

    base_url = f"http://{oam_ip}"
    if lab_config.is_ipv6():
        base_url = f"http://[{oam_ip}]"

    # Upload and apply YAML
    yaml_file = "simple_ingress_routing_http.yaml"
    local_path = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{yaml_file}")
    remote_path = f"/home/sysadmin/{yaml_file}"
    FileKeywords(ssh_connection).upload_file(local_path, remote_path, overwrite=True)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(remote_path)

    # Wait for the application pods to be running
    pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_all_pods_status("['Completed' , 'Running']")
    validate_equals(pod_status, True, "Verify pods are running")

    # Validate routing for /apple
    response_apple = ssh_connection.send(f"curl -s {base_url}/apple")
    validate_equals(response_apple[0].strip(), "apple", "Expected response for /apple")

    # Validate routing for /banana
    response_banana = ssh_connection.send(f"curl -s {base_url}/banana")
    validate_equals(response_banana[0].strip(), "banana", "Expected response for /banana")

    def teardown():
        # Clean up all default namespace resources created by the test
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)

    request.addfinalizer(teardown)


def test_simple_ingress_routing_https(request):
    """
    This test verifies ingress routing using path-based rules for HTTPS.

    Steps:
        - Create a TLS secret using OpenSSLKeywords.
        - Apply simple ingress routing resources (pods, services, ingress) with TLS configuration.
        - Validate /apple and /banana routes respond correctly over HTTPS.
        - Validate the correct TLS certificate is served.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    namespace = "pvtest"
    host_name = "konoha.rei"
    KEY_FILE = "key.crt"
    CERT_FILE = "cert.crt"
    server_url = f"https://{host_name}"
    tls_secret_name = "kanoha-secret"
    expected_issuer = f"CN={host_name}"

    # Create TLS certificate and key using the dedicated Ingress method
    OpenSSLKeywords(ssh_connection).create_ingress_certificate(key=KEY_FILE, crt=CERT_FILE, host=host_name)
    remote_key_path = f"/home/sysadmin/{KEY_FILE}"
    remote_cert_path = f"/home/sysadmin/{CERT_FILE}"

    KubectlCreateNamespacesKeywords(ssh_connection).create_namespaces(namespace)
    KubectlCreateSecretsKeywords(ssh_connection).create_secret_generic(secret_name="kanoha-secret", tls_crt=remote_cert_path, tls_key=remote_key_path, namespace=namespace)

    yaml_file = "simple_ingress_routing_https.yaml"
    local_path = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{yaml_file}")
    remote_yaml_path = f"/home/sysadmin/{yaml_file}"
    FileKeywords(ssh_connection).upload_file(local_path, remote_yaml_path, overwrite=True)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(remote_yaml_path)

    # Wait for the application pods to be running
    pod_status = KubectlGetPodsKeywords(ssh_connection).wait_for_all_pods_status("['Completed' , 'Running']")
    validate_equals(pod_status, True, "Verify pods are running")

    # Validate routing for /apple
    cmd = f"curl -k {server_url}/apple --resolve {host_name}:443:[{oam_ip}] -s"
    response_apple = ssh_connection.send(cmd)
    validate_equals(response_apple[0].strip(), "apple", "Expected response for /apple")

    # Validate routing for /banana
    cmd = f"curl -k {server_url}/banana --resolve {host_name}:443:[{oam_ip}] -s"
    response_banana = ssh_connection.send(cmd)
    validate_equals(response_banana[0].strip(), "banana", "Expected response for /banana")

    # Verify cert is issued from StepCa
    issuer = KubectlGetSecretsKeywords(ssh_connection).get_certificate_issuer(tls_secret_name, namespace)
    validate_equals(issuer, expected_issuer, f"Verify the certificate issuer is '{expected_issuer}'")

    def teardown():
        # Clean up all default namespace resources created by the test
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)

    request.addfinalizer(teardown)


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

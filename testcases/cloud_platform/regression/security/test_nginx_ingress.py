from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.certificate.kubectl_get_issuer_keywords import KubectlGetCertIssuerKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
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
    dns_name = ConfigurationManager.get_security_config().get_domain_name()
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

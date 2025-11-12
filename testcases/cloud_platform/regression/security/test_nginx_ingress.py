from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.certificate.kubectl_get_issuer_keywords import KubectlGetCertIssuerKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_create_secret_keywords import KubectlCreateSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.network.curl_response_keywords import CurlResponseKeywords
from keywords.network.ip_address_keywords import IPAddressKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


@mark.p0
def test_app_using_nginx_controller(request):
    """Deploy application using Nginx Ingress controller with External CA certificate.

    This test deploys an application that uses Nginx Ingress controller with a
    certificate signed by External CA (acme stepCA).

    Steps:
        - Deploy and apply the app file
        - Deploy and apply the globalnetworkpolicy for the acme challenge
        - Verify app status
        - Verify cert is issued from StepCa
        - Check the app url
    """
    get_logger().log_info("Starting nginx ingress controller test with External CA")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    security_config = ConfigurationManager.get_security_config()

    oam_ip = lab_config.get_floating_ip()
    dns_name = security_config.get_domain_name()
    stepca_url = security_config.get_stepca_server_url()
    expected_issuer = security_config.get_stepca_server_issuer()

    dns_resolution_status = IPAddressKeywords(oam_ip).check_dnsname_resolution(dns_name=dns_name)
    validate_equals(dns_resolution_status, True, "Verify the dns name resolution")

    # Test configuration from security config
    stepca_issuer = security_config.get_nginx_external_ca_stepca_issuer()
    pod_name = security_config.get_nginx_external_ca_pod_name()
    cert = security_config.get_nginx_external_ca_cert()
    base_url = f"https://{dns_name}/"
    deploy_app_file_name = security_config.get_nginx_external_ca_deploy_app_file_name()
    global_policy_file_name = security_config.get_nginx_external_ca_global_policy_file_name()
    kuard_file_name = security_config.get_nginx_external_ca_kuard_file_name()
    namespace = security_config.get_nginx_external_ca_namespace()
    tls_secret_name = security_config.get_nginx_external_ca_tls_secret_name()

    file_keywords = FileKeywords(ssh_connection)
    secret_keywords = KubectlGetSecretsKeywords(ssh_connection)
    apply_keywords = KubectlApplyPodsKeywords(ssh_connection)
    yaml_keywords = YamlKeywords(ssh_connection)

    # Upload and apply global policy
    get_logger().log_info("Uploading and applying global network policy")
    global_policy_remote_path = f"/home/sysadmin/{global_policy_file_name}"
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{global_policy_file_name}"), global_policy_remote_path, overwrite=False)
    apply_keywords.apply_from_yaml(global_policy_remote_path)

    # Upload and render deploy app file
    get_logger().log_info("Generating and applying deployment YAML")
    template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{deploy_app_file_name}")
    replacement_dictionary = {"stepca_server_url": stepca_url}
    deploy_app_yaml = yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dictionary, deploy_app_file_name, "/home/sysadmin")
    apply_keywords.apply_from_yaml(deploy_app_yaml)

    # Check the issuer status
    get_logger().log_info("Waiting for certificate issuer to be ready")
    issuer_keywords = KubectlGetCertIssuerKeywords(ssh_connection)
    issuer_keywords.wait_for_issuer_status(stepca_issuer, True, namespace)

    # Check the ingress pod status
    get_logger().log_info("Waiting for application pod to be running")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    try:
        pod_name = pods_keywords.get_pods(namespace=namespace).get_unique_pod_matching_prefix(starts_with=pod_name)
        pod_status = pods_keywords.wait_for_pod_status(pod_name, "Running", namespace)
        validate_equals(pod_status, True, "Verify ingress pods are running")
    except Exception as e:
        get_logger().log_error(f"Failed to find or wait for pod: {e}")
        raise

    # Generate and apply nginx ingress configuration
    get_logger().log_info("Generating and applying nginx ingress configuration")
    template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{kuard_file_name}")
    replacement_dictionary = {"dns_name": dns_name}
    nginx_yaml = yaml_keywords.generate_yaml_file_from_template(template_file, replacement_dictionary, kuard_file_name, "/home/sysadmin")
    apply_keywords.apply_from_yaml(nginx_yaml)

    # Check the cert status
    get_logger().log_info("Waiting for certificate to be issued")
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    cert_keywords.wait_for_certs_status(cert, True, namespace)

    # Check the app url
    get_logger().log_info("Verifying application accessibility")
    response = CloudRestClient().get(base_url)
    validate_equals(response.get_status_code(), 200, "Verify the app url is reachable")

    # Verify cert is issued from StepCa
    get_logger().log_info("Verifying certificate issuer")
    issuer = secret_keywords.get_certificate_issuer(tls_secret_name, namespace)
    validate_equals(issuer, expected_issuer, f"Verify the certificate issuer is '{expected_issuer}'")

    def teardown():
        """Clean up test resources."""
        get_logger().log_info("Cleaning up test resources")
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)
        KubectlFileDeleteKeywords(ssh_connection).delete_resources(global_policy_remote_path)

    request.addfinalizer(teardown)


@mark.p0
def test_simple_ingress_routing_http(request):
    """Verify ingress routing using path-based rules for HTTP.

    Steps:
        - Apply simple ingress routing resources (pods, services, ingress)
        - Validate /apple and /banana routes respond correctly
    """
    get_logger().log_info("Starting simple HTTP ingress routing test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    security_config = ConfigurationManager.get_security_config()
    oam_ip = lab_config.get_floating_ip()
    namespace = security_config.get_nginx_http_namespace()

    base_url = f"http://{oam_ip}"
    if lab_config.is_ipv6():
        base_url = f"http://[{oam_ip}]"

    # Upload and apply YAML
    get_logger().log_info("Uploading and applying ingress routing resources")
    yaml_file = "simple_ingress_routing_http.yaml"
    local_path = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{yaml_file}")
    remote_path = f"/home/sysadmin/{yaml_file}"

    file_keywords = FileKeywords(ssh_connection)
    apply_keywords = KubectlApplyPodsKeywords(ssh_connection)

    file_keywords.upload_file(local_path, remote_path, overwrite=True)
    apply_keywords.apply_from_yaml(remote_path)

    # Wait for the application pods to be running
    get_logger().log_info("Waiting for application pods to be ready")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pod_status = pods_keywords.wait_for_all_pods_status(["Completed", "Running"])
    validate_equals(pod_status, True, "Verify pods are running")

    # Validate routing for /apple with retry
    get_logger().log_info("Testing /apple route")
    curl_keywords = CurlResponseKeywords(ssh_connection)
    validate_equals_with_retry(lambda: curl_keywords.get_safe_first_response(ssh_connection.send(f"curl -s {base_url}/apple")), "apple", "Expected response for /apple", timeout=60, polling_sleep_time=2)

    # Validate routing for /banana with retry
    get_logger().log_info("Testing /banana route")
    validate_equals_with_retry(lambda: curl_keywords.get_safe_first_response(ssh_connection.send(f"curl -s {base_url}/banana")), "banana", "Expected response for /banana", timeout=60, polling_sleep_time=2)

    def teardown():
        """Clean up test resources."""
        get_logger().log_info("Cleaning up HTTP ingress test resources")
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)

    request.addfinalizer(teardown)


@mark.p0
def test_simple_ingress_routing_https(request):
    """Verify ingress routing using path-based rules for HTTPS.

    Steps:
        - Create a TLS secret using OpenSSLKeywords
        - Apply simple ingress routing resources (pods, services, ingress) with TLS configuration
        - Validate /apple and /banana routes respond correctly over HTTPS
        - Validate the correct TLS certificate is served
    """
    get_logger().log_info("Starting HTTPS ingress routing test")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    security_config = ConfigurationManager.get_security_config()
    oam_ip = lab_config.get_floating_ip()

    # Test configuration from security config
    namespace = security_config.get_nginx_https_namespace()
    host_name = security_config.get_nginx_https_host_name()
    key_file = security_config.get_nginx_https_key_file()
    cert_file = security_config.get_nginx_https_cert_file()
    server_url = f"https://{host_name}"
    tls_secret_name = security_config.get_nginx_https_tls_secret_name()
    expected_issuer = f"CN={host_name}"

    # Create TLS certificate and key using the dedicated Ingress method
    get_logger().log_info("Creating TLS certificate for ingress")
    openssl_keywords = OpenSSLKeywords(ssh_connection)
    openssl_keywords.create_ingress_certificate(key=key_file, crt=cert_file, host=host_name)

    remote_key_path = f"/home/sysadmin/{key_file}"
    remote_cert_path = f"/home/sysadmin/{cert_file}"

    get_logger().log_info("Creating namespace and TLS secret")
    namespace_keywords = KubectlCreateNamespacesKeywords(ssh_connection)
    secret_create_keywords = KubectlCreateSecretsKeywords(ssh_connection)

    namespace_keywords.create_namespaces(namespace)
    secret_create_keywords.create_secret_generic(secret_name=tls_secret_name, tls_crt=remote_cert_path, tls_key=remote_key_path, namespace=namespace)

    # Upload and apply HTTPS ingress resources
    get_logger().log_info("Uploading and applying HTTPS ingress resources")
    yaml_file = "simple_ingress_routing_https.yaml"
    local_path = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{yaml_file}")
    remote_yaml_path = f"/home/sysadmin/{yaml_file}"

    file_keywords = FileKeywords(ssh_connection)
    apply_keywords = KubectlApplyPodsKeywords(ssh_connection)

    file_keywords.upload_file(local_path, remote_yaml_path, overwrite=True)
    apply_keywords.apply_from_yaml(remote_yaml_path)

    # Wait for the application pods to be running
    get_logger().log_info("Waiting for application pods to be ready")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pod_status = pods_keywords.wait_for_all_pods_status(["Completed", "Running"])
    validate_equals(pod_status, True, "Verify pods are running")

    # Validate routing for /apple
    get_logger().log_info("Testing HTTPS /apple route")
    cmd = f"curl -k {server_url}/apple --resolve {host_name}:443:[{oam_ip}] -s"
    response_apple = ssh_connection.send(cmd)
    get_logger().log_info(f"Apple route response: {response_apple}")

    curl_keywords = CurlResponseKeywords(ssh_connection)
    validate_equals(curl_keywords.get_safe_first_response(response_apple), "apple", "Expected response for /apple")

    # Validate routing for /banana
    get_logger().log_info("Testing HTTPS /banana route")
    cmd = f"curl -k {server_url}/banana --resolve {host_name}:443:[{oam_ip}] -s"
    response_banana = ssh_connection.send(cmd)
    get_logger().log_info(f"Banana route response: {response_banana}")
    validate_equals(curl_keywords.get_safe_first_response(response_banana), "banana", "Expected response for /banana")

    # Verify certificate issuer
    get_logger().log_info("Verifying TLS certificate issuer")
    secret_keywords = KubectlGetSecretsKeywords(ssh_connection)
    issuer = secret_keywords.get_certificate_issuer(tls_secret_name, namespace)
    validate_equals(issuer, expected_issuer, f"Verify the certificate issuer is '{expected_issuer}'")

    def teardown():
        """Clean up test resources."""
        get_logger().log_info("Cleaning up HTTPS ingress test resources")
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)

    request.addfinalizer(teardown)


@mark.p1
def test_nginx_fluxcd_helmchart():
    """Verify FluxCD HelmChart resource information for nginx.

    Steps:
        - Get FluxCD helmcharts using kubectl
        - Display FluxCD HelmChart resource info for kube-system-ks-ingress-nginx
    """
    get_logger().log_info("Verifying nginx FluxCD HelmChart information")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    helm_keywords = KubectlGetHelmKeywords(ssh_connection)

    helms = helm_keywords.get_helmcharts()
    helm_names = [helm.get_name() for helm in helms.get_helmcharts()]
    get_logger().log_info(f"Retrieved helmchart names: {helm_names}")
    ingress_helm = helms.get_helmchart("kube-system-ks-ingress-nginx")

    validate_equals(ingress_helm.get_name(), "kube-system-ks-ingress-nginx", "Verify nginx HelmChart exists")
    get_logger().log_info(f"Found nginx HelmChart: {ingress_helm.get_name()}")


@mark.p1
def test_ingress_nginx_version_and_labels():
    """Verify Helm chart version and detailed pod label information for nginx controller.

    Steps:
        - Get FluxCD helmchart information (equivalent to helm list)
        - Get pods from kube-system namespace
        - Find ingress-nginx controller pod
        - Display chart name, version, app version and all relevant pod labels
    """
    get_logger().log_info("Verifying nginx ingress version and labels")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Get helm chart info from FluxCD
    helm_keywords = KubectlGetHelmKeywords(ssh_connection)
    helms = helm_keywords.get_helmcharts()
    ingress_helm = helms.get_helmchart("kube-system-ks-ingress-nginx")

    get_logger().log_info(f"HelmChart name: {ingress_helm.get_name()}")

    # Get pod labels for app version and detailed information
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods = pods_keywords.get_pods("kube-system")
    ingress_pods = pods.get_pods_start_with("ic-nginx-ingress-ingress-nginx-controller")
    validate_equals(len(ingress_pods) > 0, True, "Verify nginx controller pod exists")

    pod_name = ingress_pods[0].get_name()
    get_logger().log_info(f"Found nginx controller pod: {pod_name}")

    pod_labels = pods_keywords.get_pod_labels(pod_name, "kube-system")

    get_logger().log_info("=== Nginx Controller Pod Labels ===")
    for key, value in sorted(pod_labels.items()):
        get_logger().log_info(f"  {key}: {value}")

    app_version = pod_labels.get("app.kubernetes.io/version", "N/A")
    validate_equals(app_version != "N/A", True, "Verify nginx controller has app version label")

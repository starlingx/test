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
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.network.ip_address_keywords import IPAddressKeywords


@mark.p0
def test_app_using_nginx_controller():
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
    dns_name = ConfigurationManager.get_security_config().get_dns_name()
    dns_resolution_status = IPAddressKeywords(oam_ip).check_dnsname_resolution(dns_name=dns_name)
    validate_equals(dns_resolution_status, True, "Verify the dns name resolution")
    stepca_issuer = "stepca-issuer"
    pod_name = "kuard"
    cert = "kuard-ingress-tls"
    base_url = f"https://{dns_name}/"
    deploy_app_file_name = "deploy_app.yaml"
    global_policy_file_name = "global_policy.yaml"
    kuard_file_name = "kuard.yaml"
    namespace = "pvtest"

    file_keywords = FileKeywords(ssh_connection)
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{deploy_app_file_name}"), f"/home/sysadmin/{deploy_app_file_name}", overwrite=False)
    file_keywords.upload_file(get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{global_policy_file_name}"), f"/home/sysadmin/{global_policy_file_name}", overwrite=False)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(f"/home/sysadmin/{global_policy_file_name}")
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(f"/home/sysadmin/{deploy_app_file_name}")
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

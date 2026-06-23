import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_greater_than, validate_list_contains, validate_str_contains, validate_str_contains_with_retry
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.certificate.kubectl_get_issuer_keywords import KubectlGetCertIssuerKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.helm.kubectl_get_helm_keywords import KubectlGetHelmKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_get_namespaces_keywords import KubectlGetNamespacesKeywords
from keywords.k8s.pods.kubectl_apply_pods_keywords import KubectlApplyPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_delete_secret_keywords import KubectlDeleteSecretsKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


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
    security_config = ConfigurationManager.get_security_config()
    ssh_user_home = security_config.get_ssh_user_home()

    app_name = "cert-manager"
    chart_name = "cert-manager"
    namespace = "cert-manager"
    label_key = "test"
    label_value = "cm_label"
    label = f"{label_key}: {label_value}"
    k8s_label = f"{label_key}={label_value}"

    cm_override_file_name = "cm_override_values.yaml"

    template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{cm_override_file_name}")
    replacement_dictionary = {"cm_label_key": label_key, "cm_label_value": label_value}
    get_logger().log_test_case_step(f"Creating resource from file {template_file}")
    remote_path = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, f"{cm_override_file_name}", ssh_user_home)

    get_logger().log_test_case_step(f"Helm override for {app_name} with custom values")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override(remote_path, app_name, chart_name, namespace)

    get_logger().log_test_case_step(f"Verify helm override show for {app_name} with custom values")
    SystemHelmOverrideKeywords(ssh_connection).verify_helm_user_override(label, app_name, chart_name, namespace)
    get_logger().log_test_case_step(f"Re-apply the {app_name} application")

    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)

    system_application_object = system_application_apply_output.get_system_application_object()
    validate_str_contains(system_application_object.get_name(), app_name, "Apply cert-manager")
    validate_str_contains(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Apply cert-manager")

    pods_keywords = KubectlGetPodsKeywords(ssh_connection)

    def get_pod_status():
        pod_status = pods_keywords.get_pods(namespace=namespace, label=k8s_label).get_pods_start_with(app_name)[0].get_status()
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
    security_config = ConfigurationManager.get_security_config()
    ssh_user_home = security_config.get_ssh_user_home()
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

    def teardown_namespace():
        get_logger().log_test_case_step("Deleting testcert namespace")
        ns_list = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces()

        if ns_list.is_namespace(namespace_name=namespace):
            get_logger().log_test_case_step("Deleting testcert namespace")
            KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace=namespace)
        else:
            get_logger().log_test_case_step("testcert namespace does not exist")

    request.addfinalizer(teardown_namespace)

    kubectl_create_ns_keyword = KubectlCreateNamespacesKeywords(ssh_connection)
    kubectl_create_ns_keyword.create_namespaces(namespace)
    ns_list = KubectlGetNamespacesKeywords(ssh_connection).get_namespaces()

    validate_equals(ns_list.is_namespace(namespace_name=namespace), True, "create namespace")

    cluster_issuer_template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{cluster_issuer_file_name}")
    issuer_replacement_dictionary = {"cluster_issuer": cluster_issuer}
    cluster_issuer_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(cluster_issuer_template_file, issuer_replacement_dictionary, f"{cluster_issuer_file_name}", ssh_user_home)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(cluster_issuer_yaml)

    root_cacert_template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{root_cacert_file_name}")
    root_cacert_replacement_dictionary = {"root_ca_cert": root_ca_cert, "root_ca_secret": root_ca_secret, "cluster_issuer": cluster_issuer, "namespace": namespace}
    root_cacert_issuer_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(root_cacert_template_file, root_cacert_replacement_dictionary, f"{root_cacert_file_name}", ssh_user_home)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(root_cacert_issuer_yaml)
    platform_issuer_template_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{platform_issuer_file_name}")
    platform_issuer_replacement_dictionary = {"root_ca_secret": root_ca_secret, "platform_issuer": platform_issuer, "namespace": namespace}
    platform_issuer_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(platform_issuer_template_file, platform_issuer_replacement_dictionary, f"{platform_issuer_file_name}", ssh_user_home)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(platform_issuer_yaml)

    KubectlGetCertIssuerKeywords(ssh_connection).wait_for_issuer_status(platform_issuer, True, namespace)
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(root_ca_cert, True, namespace)
    root_ca_list_of_secrets = KubectlGetSecretsKeywords(ssh_connection).get_secret_names(namespace=namespace)
    validate_list_contains(root_ca_secret, root_ca_list_of_secrets, "Root ca secret")
    KubectlGetCertIssuerKeywords(ssh_connection).wait_for_issuer_status(platform_issuer, True, namespace)

    registry_local_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{registry_local_cert_file_name}")
    registry_replacement_dictionary = {"registry_local_cert": registry_local_cert, "registry_local_secret": registry_local_secret, "platform_issuer": platform_issuer, "floating_ip": oam_ip, "namespace": namespace}
    registry_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(registry_local_file, registry_replacement_dictionary, f"{registry_local_cert_file_name}", ssh_user_home)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(registry_yaml)
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(registry_local_cert, True, namespace)

    secret_keywords_ns = KubectlGetSecretsKeywords(ssh_connection)

    def get_list_of_secrets():
        return secret_keywords_ns.get_secret_names(namespace=namespace)

    validate_str_contains_with_retry(get_list_of_secrets, registry_local_secret, "Registry local secret", timeout=10)
    restapi_gui_file = get_stx_resource_path(f"resources/cloud_platform/security/cert_manager/{restapi_gui_cert_file_name}")
    restapi_replacement_dictionary = {"restapi_gui_cert": restapi_gui_cert, "restapi_gui_secret": restapi_gui_secret, "platform_issuer": platform_issuer, "floating_ip": oam_ip, "namespace": namespace}
    restapi_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(restapi_gui_file, restapi_replacement_dictionary, f"{restapi_gui_cert_file_name}", ssh_user_home)
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(restapi_yaml)
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(restapi_gui_cert, True, namespace)
    validate_str_contains_with_retry(get_list_of_secrets, restapi_gui_secret, "restapi gui secret", timeout=10)


@mark.p1
def test_cert_manager_fluxcd_helmchart():
    """Verify FluxCD HelmChart resource information for cert-manager.

    Steps:
        - Get FluxCD helmcharts using kubectl
        - Verify that the cert-manager HelmChart resource exists
    """
    get_logger().log_test_case_step("Verifying cert-manager FluxCD HelmChart information")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    helms = KubectlGetHelmKeywords(ssh_connection).get_helmcharts()

    cert_manager_helm = helms.get_helmchart("cert-manager-cert-manager")
    validate_equals(cert_manager_helm.get_name(), "cert-manager-cert-manager", "Verify cert-manager HelmChart exists")


@mark.p1
def test_cert_manager_helm_chart_version_and_labels():
    """Verify Helm chart version and pod label information for cert-manager.

    Steps:
        - Get FluxCD helmchart information and verify chart name and version
        - Get pods from cert-manager namespace
        - Find cert-manager controller pod
        - Verify app version and helm chart labels on the pod
    """
    get_logger().log_test_case_step("Verifying cert-manager helm chart version and pod labels")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    namespace = "cert-manager"

    cert_manager_helm = KubectlGetHelmKeywords(ssh_connection).get_helmcharts().get_helmchart("cert-manager-cert-manager")
    validate_equals(cert_manager_helm.get_chart(), "cert-manager", "Verify cert-manager chart name")
    validate_equals(cert_manager_helm.get_version() is not None, True, "Verify cert-manager HelmChart has a version")

    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    cert_manager_pods = pods_keywords.get_pods(namespace).get_pods_start_with("cm-cert-manager")
    validate_equals(len(cert_manager_pods) > 0, True, "Verify cert-manager controller pod exists")

    pod_labels = pods_keywords.get_pod_labels(cert_manager_pods[0].get_name(), namespace)
    validate_equals("app.kubernetes.io/version" in pod_labels, True, "Verify cert-manager pod has app.kubernetes.io/version label")
    validate_equals("helm.sh/chart" in pod_labels, True, "Verify cert-manager pod has helm.sh/chart label")


@mark.p1
def test_cert_manager_certificate_renewal(request: FixtureRequest):
    """Verify cert-manager automatically renews a short-lived certificate.

    Creates a short-lived certificate and waits for cert-manager to automatically
    renew it. Renewal is confirmed by comparing the serial number and notAfter
    date before and after the renewal window.

    Steps:
        - Create namespace and self-signed issuer
        - Deploy short-lived certificate
        - Capture initial serial number and notAfter date
        - Wait for cert-manager to renew the certificate
        - Verify serial number has changed
        - Verify new notAfter is later than original

    Teardown:
        - Delete the test namespace

    Args:
        request (FixtureRequest): pytest request object for finalizer registration.
    """
    security_config = ConfigurationManager.get_security_config()
    namespace = security_config.get_cert_renewal_namespace()
    issuer_name = security_config.get_cert_renewal_issuer_name()
    cert_name = security_config.get_cert_renewal_cert_name()
    secret_name = security_config.get_cert_renewal_secret_name()
    renewal_timeout = security_config.get_cert_renewal_timeout()

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    def teardown():
        get_logger().log_test_case_step(f"Deleting namespace {namespace}")
        KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(namespace)

    request.addfinalizer(teardown)

    KubectlCreateNamespacesKeywords(ssh_connection).create_namespaces(namespace)

    template_file = get_stx_resource_path("resources/cloud_platform/security/cert_manager/cert_renewal_test.yaml")
    replacement_dict = {
        "namespace": namespace,
        "issuer_name": issuer_name,
        "cert_name": cert_name,
        "secret_name": secret_name,
        "duration": security_config.get_cert_renewal_duration(),
        "renew_before": security_config.get_cert_renewal_renew_before(),
    }
    rendered_yaml = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dict, "cert_renewal_test.yaml", security_config.get_ssh_user_home())
    KubectlApplyPodsKeywords(ssh_connection).apply_from_yaml(rendered_yaml)

    KubectlGetCertIssuerKeywords(ssh_connection).wait_for_issuer_status(issuer_name, True, namespace)
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status(cert_name, True, namespace)

    secret_keywords = KubectlGetSecretsKeywords(ssh_connection)
    initial_secret = secret_keywords.get_secret_json_output(secret_name, namespace)
    initial_serial = initial_secret.get_certificate_serial()
    initial_not_after = initial_secret.get_certificate_not_after()
    get_logger().log_test_case_step(f"Initial certificate serial: {initial_serial}, notAfter: {initial_not_after}")

    def serial_has_changed():
        renewed_secret = secret_keywords.get_secret_json_output(secret_name, namespace)
        return renewed_secret.get_certificate_serial() != initial_serial

    validate_equals_with_retry(serial_has_changed, True, "Verify certificate serial number changed after renewal", renewal_timeout, 60)

    renewed_secret = secret_keywords.get_secret_json_output(secret_name, namespace)
    renewed_serial = renewed_secret.get_certificate_serial()
    renewed_not_after = renewed_secret.get_certificate_not_after()
    get_logger().log_test_case_step(f"Renewed certificate serial: {renewed_serial}, notAfter: {renewed_not_after}")

    validate_equals(renewed_serial != initial_serial, True, "Verify certificate serial number changed after renewal")
    validate_equals(renewed_not_after > initial_not_after, True, "Verify renewed certificate notAfter is later than original")


@mark.p1
def test_cert_mon_certificate_renewal_due_to_secret_deletion():
    """Verify cert-manager renews the openldap certificate after its secret is deleted.

    Validates the cert-mon certificate renewal workflow by confirming that deleting
    the certificate secret triggers cert-manager to issue a new certificate with an
    updated serial number and expiration date.

    Steps:
        - Read the original certificate dates and serial from the openldap cert file
        - Delete the system-openldap-local-certificate secret in the deployment namespace
        - Wait for cert-manager to issue a renewed certificate
        - Verify the renewed certificate has a different serial number
        - Verify the renewed certificate has a later notAfter date
        - Describe the Certificate resource and confirm cert-manager issued the renewal
    """
    cert_path = "/etc/ldap/certs/openldap-cert.crt"
    secret_name = "system-openldap-local-certificate"
    namespace = "deployment"
    cert_resource_name = "system-openldap-local-certificate"
    renewal_timeout = 300

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_keywords = OpenSSLKeywords(ssh_connection)

    get_logger().log_test_case_step("Reading original certificate info from openldap cert file")
    original_cert_info = openssl_keywords.get_cert_info_from_file(cert_path)
    original_serial = original_cert_info.get("serial")
    original_not_after = original_cert_info.get("not_after")
    get_logger().log_test_case_step(f"Original certificate: serial={original_serial}, notAfter={original_not_after}")

    get_logger().log_test_case_step(f"Deleting secret {secret_name} in namespace {namespace} to trigger renewal")
    KubectlDeleteResourceKeywords(ssh_connection).delete_resource("secret", secret_name, namespace)

    get_logger().log_test_case_step("Waiting for cert-manager to issue a renewed certificate")

    def serial_has_changed():
        renewed_info = openssl_keywords.get_cert_info_from_file(cert_path)
        return renewed_info.get("serial") != original_serial

    validate_equals_with_retry(serial_has_changed, True, "Verify renewed certificate serial differs from original", renewal_timeout, 10)

    get_logger().log_test_case_step("Reading renewed certificate info")
    renewed_cert_info = openssl_keywords.get_cert_info_from_file(cert_path)
    renewed_serial = renewed_cert_info.get("serial")
    renewed_not_after = renewed_cert_info.get("not_after")
    get_logger().log_test_case_step(f"Renewed certificate: serial={renewed_serial}, notAfter={renewed_not_after}")

    validate_equals(renewed_serial != original_serial, True, "Renewed certificate serial should differ from original")
    validate_equals(renewed_not_after > original_not_after, True, "Renewed certificate notAfter should be later than original")

    get_logger().log_test_case_step(f"Describing Certificate resource {cert_resource_name} to confirm cert-manager issued the renewal")
    describe_output = ssh_connection.send(export_k8s_config(f"kubectl describe certificate {cert_resource_name} -n {namespace}"))
    raw_describe = "\n".join(describe_output) if isinstance(describe_output, list) else describe_output
    validate_str_contains(raw_describe, "cert-manager", "Certificate resource description should reference cert-manager")
    validate_str_contains(raw_describe, "Issuing", "Certificate events should contain Issuing event from cert-manager")


@mark.p1
@mark.lab_has_subcloud
def test_cert_mon_sync_in_dc_environment(request: FixtureRequest):
    """Verify cert-mon certificate sync between central node and subcloud in DC environment.

    Validates that after DC deployment all certificates are ready, that the adminep
    CA certificate is identical on both the central node and the subcloud, and that
    deleting the secret on the central node triggers cert-manager to renew it with
    the renewed certificate remaining in sync across both nodes.

    Steps:
        - Verify all certificates in all namespaces have READY=True on central node
        - Get the subcloud region_name via dcmanager subcloud show
        - Retrieve the adminep CA certificate from the central node (dc-cert namespace)
        - Retrieve the sc-adminep-ca-certificate from the subcloud (sc-cert namespace)
        - Verify both certificates are identical before deletion
        - Delete the adminep CA certificate secret on the central node
        - Wait for cert-manager to renew the certificate on the central node
        - Verify the renewed certificate differs from the original
        - Verify the renewed certificate is synced to the subcloud
        - Describe the Certificate resource and confirm cert-manager issued the renewal
    """
    dc_namespace = "dc-cert"
    sc_namespace = "sc-cert"
    sc_secret_name = "sc-adminep-ca-certificate"
    renewal_timeout = 300

    central_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Getting subcloud name and region_name from dcmanager")
    subcloud_list = DcManagerSubcloudListKeywords(central_ssh).get_dcmanager_subcloud_list()
    managed_online_subclouds = [
        sc for sc in subcloud_list.get_dcmanager_subcloud_list_objects()
        if sc.get_management() == "managed" and sc.get_availability() == "online"
    ]
    validate_greater_than(
        len(managed_online_subclouds), 0,
        "No managed/online subclouds available for DC cert sync test"
    )
    subcloud = managed_online_subclouds[0]
    subcloud_name = subcloud.get_name()

    subcloud_show = DcManagerSubcloudShowKeywords(central_ssh).get_dcmanager_subcloud_show(subcloud_name)
    region_name = subcloud_show.get_dcmanager_subcloud_show_object().get_region_name()
    get_logger().log_test_case_step(f"Subcloud: {subcloud_name}, region_name: {region_name}")

    central_secret_name = f"{region_name}-adminep-ca-certificate"
    cert_resource_name = central_secret_name

    def cleanup_renewed_secret():
        get_logger().log_test_case_step(f"Teardown: waiting for cert-manager to recreate {central_secret_name} if missing")
        secret_keywords_cleanup = KubectlGetSecretsKeywords(central_ssh)
        timeout_time = time.time() + 300
        while time.time() < timeout_time:
            try:
                secret_keywords_cleanup.get_secret_json_output(central_secret_name, dc_namespace)
                get_logger().log_test_case_step(f"Teardown: secret {central_secret_name} exists, cleanup complete")
                return
            except Exception:
                time.sleep(10)
        get_logger().log_test_case_step(f"Teardown: secret {central_secret_name} was not recreated within timeout")

    request.addfinalizer(cleanup_renewed_secret)

    get_logger().log_test_case_step("Verifying all certificates are READY on the central node")
    all_certs = KubectlGetCertStatusKeywords(central_ssh).get_certificates()
    for cert in all_certs.get_certs():
        validate_equals(cert.get_ready(), "True", f"Certificate {cert.get_name()} should be READY=True")

    get_logger().log_test_case_step(f"Retrieving initial certificate from central node secret: {central_secret_name}")
    central_secret_keywords = KubectlGetSecretsKeywords(central_ssh)
    initial_central_secret = central_secret_keywords.get_secret_json_output(central_secret_name, dc_namespace)
    initial_central_cert = initial_central_secret.get_decoded_data("tls.crt")
    initial_central_serial = initial_central_secret.get_certificate_serial()
    get_logger().log_test_case_step(f"Initial central certificate serial: {initial_central_serial}")

    get_logger().log_test_case_step(f"Retrieving initial certificate from subcloud secret: {sc_secret_name}")
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    initial_sc_secret = KubectlGetSecretsKeywords(subcloud_ssh).get_secret_json_output(sc_secret_name, sc_namespace)
    initial_sc_cert = initial_sc_secret.get_decoded_data("tls.crt")

    get_logger().log_test_case_step("Verifying central and subcloud certificates are identical before deletion")
    validate_equals(initial_central_cert, initial_sc_cert, "Central and subcloud certificates should be identical before deletion")

    get_logger().log_test_case_step(f"Deleting secret {central_secret_name} on central node to trigger renewal")
    KubectlDeleteSecretsKeywords(central_ssh).delete_secret(central_secret_name, dc_namespace)

    get_logger().log_test_case_step("Waiting for cert-manager to renew the certificate on the central node")

    def central_serial_has_changed():
        try:
            renewed_secret = central_secret_keywords.get_secret_json_output(central_secret_name, dc_namespace)
            return renewed_secret.get_certificate_serial() != initial_central_serial
        except Exception:
            return False

    validate_equals_with_retry(central_serial_has_changed, True, "Renewed central certificate serial should differ from original", renewal_timeout, 10)

    get_logger().log_test_case_step("Retrieving renewed certificate from central node")
    renewed_central_secret = central_secret_keywords.get_secret_json_output(central_secret_name, dc_namespace)
    renewed_central_cert = renewed_central_secret.get_decoded_data("tls.crt")
    renewed_central_serial = renewed_central_secret.get_certificate_serial()
    get_logger().log_test_case_step(f"Renewed central certificate serial: {renewed_central_serial}")

    validate_equals(renewed_central_serial != initial_central_serial, True, "Renewed central certificate serial should differ from original")

    get_logger().log_test_case_step("Waiting for renewed certificate to sync to subcloud")

    subcloud_secret_keywords = KubectlGetSecretsKeywords(subcloud_ssh)

    def subcloud_cert_synced():
        renewed_sc_secret = subcloud_secret_keywords.get_secret_json_output(sc_secret_name, sc_namespace)
        return renewed_sc_secret.get_decoded_data("tls.crt") == renewed_central_cert

    validate_equals_with_retry(subcloud_cert_synced, True, "Renewed certificate should sync to subcloud", renewal_timeout, 10)

    get_logger().log_test_case_step("Verifying renewed certificate is identical on central node and subcloud")
    renewed_sc_secret = subcloud_secret_keywords.get_secret_json_output(sc_secret_name, sc_namespace)
    renewed_sc_cert = renewed_sc_secret.get_decoded_data("tls.crt")
    validate_equals(renewed_central_cert, renewed_sc_cert, "Renewed central and subcloud certificates should be identical")

    get_logger().log_test_case_step(f"Describing Certificate resource {cert_resource_name} to confirm cert-manager issued the renewal")
    describe_output = central_ssh.send(export_k8s_config(f"kubectl describe certificate {cert_resource_name} -n {dc_namespace}"))
    raw_describe = "\n".join(describe_output) if isinstance(describe_output, list) else describe_output
    validate_str_contains(raw_describe, "cert-manager", "Certificate description should reference cert-manager")
    validate_str_contains(raw_describe, "Issuing", "Certificate events should contain Issuing event from cert-manager")

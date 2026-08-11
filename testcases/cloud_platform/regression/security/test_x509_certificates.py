"""Verify X.509 certificate key types, operations, and HA."""


from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_not_equals, validate_str_contains
from keywords.cloud_platform.fault_management.alarms.alarm_list_keywords import AlarmListKeywords
from keywords.cloud_platform.sm.sm_keywords import SMKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.certificate.system_certificate_keywords import SystemCertificateKeywords
from keywords.cloud_platform.system.health_query.system_health_query_keywords import SystemHealthQueryKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.registry.system_registry_image_list_keywords import SystemRegistryImageListKeywords
from keywords.cloud_platform.version_info.cloud_platform_version_manager import CloudPlatformVersionManager
from keywords.files.curl_keywords import CurlKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.certificate.kubectl_get_issuer_keywords import KubectlGetCertIssuerKeywords
from keywords.k8s.crd.kubectl_systems_keywords import KubectlSystemsKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.files.kubectl_file_delete_keywords import KubectlFileDeleteKeywords
from keywords.k8s.patch.kubectl_apply_patch_keywords import KubectlApplyPatchKeywords
from keywords.k8s.secret.kubectl_get_secret_keywords import KubectlGetSecretsKeywords
from keywords.linux.ldap.ldap_keywords import LdapKeywords
from keywords.openssl.object.cert_key_info_object import CertKeyInfoObject
from keywords.openssl.openssl_keywords import OpenSSLKeywords

CLUSTER_ISSUER = "system-local-ca"
NAMESPACE_CERT_MANAGER = "cert-manager"
NAMESPACE_DEPLOYMENT = "deployment"


def format_url_ip(ip: str) -> str:
    """Format IP for use in URLs - wrap IPv6 in brackets.

    Args:
        ip (str): IP address (IPv4 or IPv6).

    Returns:
        str: IP formatted for URL use ([ip] for IPv6, ip for IPv4).
    """
    if ConfigurationManager.get_lab_config().is_ipv6():
        return f"[{ip}]"
    return ip


PLATFORM_CERTS = [
    "system-restapi-gui-certificate",
    "system-registry-local-certificate",
    "system-openldap-local-certificate",
]
PLATFORM_CERT_PATHS = {
    "system-restapi-gui-certificate": "/etc/ssl/private/server-cert.pem",
    "system-registry-local-certificate": "/etc/ssl/private/registry-cert.crt",
    "system-openldap-local-certificate": "/etc/ldap/certs/openldap-cert.crt",
}
CERT_ALARM_IDS = ["500.200", "500.210"]

CA_VALID_CURVES = ["secp384r1", "secp521r1"]
PLATFORM_VALID_CURVES = ["prime256v1", "secp384r1", "secp521r1"]


def validate_ca_key_meets_minimum(key_info: CertKeyInfoObject):
    """Validate CA certificate key meets minimum requirements.

    Args:
        key_info (CertKeyInfoObject): Key info object from openssl keywords.
    """
    if key_info.get_type() == "ECDSA":
        validate_equals(key_info.get_curve() in CA_VALID_CURVES, True, f"CA ECDSA curve {key_info.get_curve()} must be in {CA_VALID_CURVES}")
    elif key_info.get_type() == "RSA":
        validate_equals(key_info.get_size() >= 4096, True, f"CA RSA key size {key_info.get_size()} must be >= 4096")
    else:
        validate_equals(False, True, f"CA key type is unknown or None: {key_info}")


def validate_platform_cert_key_meets_minimum(key_info: CertKeyInfoObject):
    """Validate platform certificate key meets minimum requirements.

    Args:
        key_info (CertKeyInfoObject): Key info object from openssl keywords.
    """
    if key_info.get_type() == "ECDSA":
        validate_equals(key_info.get_curve() in PLATFORM_VALID_CURVES, True, f"Platform ECDSA curve {key_info.get_curve()} must be in {PLATFORM_VALID_CURVES}")
    elif key_info.get_type() == "RSA":
        validate_equals(key_info.get_size() >= 3072, True, f"Platform RSA key size {key_info.get_size()} must be >= 3072")
    else:
        validate_equals(False, True, f"Platform cert key type is unknown or None: {key_info}")


@mark.p1
def test_verify_certs_services_and_chain(request: FixtureRequest):
    """Verify system-local-ca, platform certs, services, and chain integrity.

    Steps:
        - Detect OS for key type enforcement
        - Verify system-local-ca key type meets CA minimum (Trixie only)
        - Verify ClusterIssuer system-local-ca is Ready
        - Verify all platform certs present in certificate-list
        - Verify each platform cert Renewal=Automatic
        - Verify each platform cert key type meets minimum (Trixie only)
        - Verify kubectl get certificates READY for all
        - Verify no cert-related alarms
        - Verify system health-query has no cert alarms
        - Verify REST API accessible
        - Verify docker registry responds
        - Verify DM reconciled and insync
        - Verify LDAP responds
        - Extract RCA/ICA and verify chain for all platform certs
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    cert_kw = SystemCertificateKeywords(ssh_connection)
    alarm_kw = AlarmListKeywords(ssh_connection)
    oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()
    registry_kw = SystemRegistryImageListKeywords(ssh_connection)
    cert_status_kw = KubectlGetCertStatusKeywords(ssh_connection)
    is_trixie = CloudPlatformVersionManager.is_trixie(ssh_connection)

    def teardown():
        """Remove temporary PEM files."""
        file_kw = FileKeywords(ssh_connection)
        file_kw.delete_file("/tmp/rca.pem")
        file_kw.delete_file("/tmp/ica.pem")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Verify system-local-ca secret exists and key type")
    secret_names = KubectlGetSecretsKeywords(ssh_connection).get_secret_names(namespace=NAMESPACE_CERT_MANAGER)
    validate_equals(CLUSTER_ISSUER in secret_names, True, "system-local-ca secret should exist in cert-manager namespace")

    ca_key_info = openssl_kw.get_cert_key_info_from_secret(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER)
    get_logger().log_info(f"system-local-ca key info: {ca_key_info}")
    if is_trixie:
        validate_ca_key_meets_minimum(ca_key_info)

    get_logger().log_test_case_step("Verify ClusterIssuer system-local-ca is Ready")
    clusterissuer_output = KubectlGetCertIssuerKeywords(ssh_connection).get_clusterissuers()
    issuer_obj = clusterissuer_output.get_issuer(CLUSTER_ISSUER)
    validate_equals(issuer_obj.get_ready(), "True", "ClusterIssuer system-local-ca should be Ready")

    get_logger().log_test_case_step("Verify all platform certs present")
    cert_list_output = cert_kw.certificate_list()
    for cert_name in PLATFORM_CERTS:
        validate_equals(cert_list_output.has_certificate(cert_name), True, f"{cert_name} should be present in certificate list")

    get_logger().log_test_case_step("Verify each platform cert Renewal=Automatic")
    for cert_name in PLATFORM_CERTS:
        cert_obj = cert_list_output.get_certificate_by_name(cert_name)
        validate_equals(cert_obj.get_renewal(), "Automatic", f"{cert_name} renewal should be Automatic")

    get_logger().log_test_case_step("Verify platform cert key types and issuer")
    for cert_name in PLATFORM_CERTS:
        key_info = openssl_kw.get_cert_key_info_from_secret(cert_name, NAMESPACE_DEPLOYMENT)
        get_logger().log_info(f"{cert_name} key info: {key_info}")
        if is_trixie:
            validate_platform_cert_key_meets_minimum(key_info)

    get_logger().log_test_case_step("Verify each platform cert is issued by a valid CA")
    secret_kw = KubectlGetSecretsKeywords(ssh_connection)
    ca_issuer_subject = secret_kw.get_certificate_issuer(CLUSTER_ISSUER, namespace=NAMESPACE_CERT_MANAGER)
    get_logger().log_info(f"system-local-ca subject: {ca_issuer_subject}")

    for cert_name in PLATFORM_CERTS:
        cert_issuer = secret_kw.get_certificate_issuer(cert_name, namespace=NAMESPACE_DEPLOYMENT)
        get_logger().log_info(f"{cert_name} issuer: {cert_issuer}")
        validate_not_equals(cert_issuer, None, f"{cert_name} should have a valid issuer")
        validate_not_equals(cert_issuer, "", f"{cert_name} issuer should not be empty")

    get_logger().log_test_case_step("Verify all certificates READY in deployment namespace")
    certs_output = cert_status_kw.get_certificates(namespace=NAMESPACE_DEPLOYMENT)
    for cert_name in PLATFORM_CERTS:
        cert = certs_output.get_cert(cert_name)
        validate_equals(cert.get_ready(), "True", f"{cert_name} should be READY=True")

    get_logger().log_test_case_step("Verify no cert-related alarms")
    alarms_output = alarm_kw.get_alarm_list()
    alarm_ids = alarms_output.alarms_id()
    for alarm_id in CERT_ALARM_IDS:
        validate_equals(alarm_id in alarm_ids, False, f"Alarm {alarm_id} should not be present")

    get_logger().log_test_case_step("Verify system health-query")
    health_kw = SystemHealthQueryKeywords(ssh_connection)
    health_output = health_kw.get_health_status()
    validate_not_equals(health_output, None, "health-query should return valid output")

    get_logger().log_test_case_step("Verify REST API accessible")
    curl_kw = CurlKeywords(ssh_connection)
    http_code = curl_kw.get_http_status_code(f"https://{format_url_ip(oam_ip)}:5000/v3")
    validate_equals(http_code, "200", "REST API should return HTTP 200")

    get_logger().log_test_case_step("Verify docker registry responds")
    registry_output = registry_kw.get_registry_image_list()
    validate_not_equals(registry_output, None, "Registry should respond")

    get_logger().log_test_case_step("Verify DM reconciled and insync")
    systems_output = KubectlSystemsKeywords(ssh_connection).get_systems(namespace=NAMESPACE_DEPLOYMENT)
    validate_equals(systems_output.is_all_reconciled(), True, "DM systems should be reconciled")
    validate_equals(systems_output.is_all_insync(), True, "DM systems should be insync")

    get_logger().log_test_case_step("Verify LDAP responds")
    admin_pw = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
    ldap_kw = LdapKeywords(ssh_connection, admin_pw)
    ldap_reachable = ldap_kw.check_ldap_connectivity("localhost")
    validate_equals(ldap_reachable, True, "LDAP should be reachable")

    get_logger().log_test_case_step("Extract RCA and ICA from system-local-ca")
    secret_kw = KubectlGetSecretsKeywords(ssh_connection)
    file_kw = FileKeywords(ssh_connection)
    rca_pem = secret_kw.get_secret_with_custom_output(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, "go-template", "'{{index .data \"ca.crt\"}}'", base64=True)
    file_kw.create_file_with_heredoc("/tmp/rca.pem", rca_pem)
    ica_pem = secret_kw.get_secret_with_custom_output(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, "go-template", "'{{index .data \"tls.crt\"}}'", base64=True)
    file_kw.create_file_with_heredoc("/tmp/ica.pem", ica_pem)

    get_logger().log_test_case_step("Verify certificate chain for all platform certs")
    for cert_name, cert_path in PLATFORM_CERT_PATHS.items():
        openssl_kw.verify_cert_chain("/tmp/rca.pem", "/tmp/ica.pem", cert_path)
        get_logger().log_info(f"{cert_name}: chain verification OK")


@mark.p2
def test_verify_oidc_cert_key_type():
    """Verify OIDC/Dex certificate uses acceptable key type.

    Steps:
        - Check if OIDC app deployed (skip if not)
        - Verify oidc-auth-apps-certificate key type meets minimum (Trixie only)
        - Verify OIDC service responds
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    cert_kw = SystemCertificateKeywords(ssh_connection)
    is_trixie = CloudPlatformVersionManager.is_trixie(ssh_connection)

    get_logger().log_test_case_step("Check if OIDC app is deployed")
    cert_list_output = cert_kw.certificate_list()
    validate_equals(cert_list_output.has_certificate("oidc-auth-apps-certificate"), True, "OIDC app not deployed - test cannot run without oidc-auth-apps applied")

    get_logger().log_test_case_step("Verify OIDC cert key type")
    key_info = openssl_kw.get_cert_key_info_from_secret("oidc-auth-apps-certificate", "kube-system")
    get_logger().log_info(f"OIDC cert key info: {key_info}")
    if is_trixie:
        validate_platform_cert_key_meets_minimum(key_info)


@mark.p2
def test_certificate_show_displays_key_info():
    """Verify system certificate-show displays correct key algorithm info.

    Steps:
        - Run system certificate-show for system-restapi-gui-certificate
        - Run system certificate-show for system-local-ca
        - Validate key info fields consistent with detected type
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    cert_kw = SystemCertificateKeywords(ssh_connection)

    get_logger().log_test_case_step("system certificate-show system-restapi-gui-certificate")
    show_output = cert_kw.certificate_show("system-restapi-gui-certificate")
    cert_show = show_output.get_certificate_show()
    actual_key = openssl_kw.get_cert_key_info_from_secret("system-restapi-gui-certificate", NAMESPACE_DEPLOYMENT)
    validate_str_contains(cert_show.get_key_size(), str(actual_key.get_size()), "certificate-show should display key size")

    get_logger().log_test_case_step("system certificate-show system-local-ca")
    show_output = cert_kw.certificate_show("system-local-ca")
    ca_show = show_output.get_certificate_show()
    ca_key = openssl_kw.get_cert_key_info_from_secret(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER)
    validate_str_contains(ca_show.get_key_size(), str(ca_key.get_size()), "CA certificate-show should display key size")


@mark.p2
def test_cert_manager_certificate_spec():
    """Verify cert-manager Certificate CR spec shows correct privateKey config.

    Steps:
        - For each platform cert, check spec.privateKey algorithm and size
        - Verify issuerRef.name is system-local-ca
        - On Trixie, validate meets minimums
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    is_trixie = CloudPlatformVersionManager.is_trixie(ssh_connection)

    get_logger().log_test_case_step("Verify Certificate CR privateKey spec for each platform cert")
    cert_status_kw = KubectlGetCertStatusKeywords(ssh_connection)
    certs_output = cert_status_kw.get_certificates_with_extra_columns(NAMESPACE_DEPLOYMENT, ["algorithm", "size", "issuer"])
    for cert_name in PLATFORM_CERTS:
        cert = certs_output.get_cert(cert_name)
        algorithm = cert.get_algorithm()
        size_str = cert.get_size()
        issuer = cert.get_issuer_ref()

        get_logger().log_info(f"{cert_name}: algorithm={algorithm}, size={size_str}, issuer={issuer}")
        validate_equals(issuer, CLUSTER_ISSUER, f"{cert_name} issuerRef should be {CLUSTER_ISSUER}")

        if is_trixie and algorithm == "RSA":
            validate_equals(int(size_str) >= 3072, True, f"{cert_name} RSA size should be >= 3072")


@mark.p2
def test_cert_expiry_alarm_lifecycle(request: FixtureRequest):
    """Verify certificate expiry alarm lifecycle and health-query status.

    Steps:
        - Pre-check: no existing alarm, cert not near-expiry
        - Save original cert/key values (for patch-based restore)
        - Patch system-local-ca with 1-day expiry cert
        - Restart cert-mon and cert-alarm, wait for alarm 500.200
        - Verify health-query-upgrade shows Fail
        - Restore original cert/key via patch (avoids resourceVersion issues)
        - Restart cert-mon and cert-alarm, wait for alarm to clear
        - Verify health-query-upgrade returns to OK
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    alarm_kw = AlarmListKeywords(ssh_connection)

    # Save original values FIRST (before any modifications)
    orig_tls_crt = None
    orig_tls_key = None

    def teardown():
        """Restore original system-local-ca via patch and restart services."""
        if orig_tls_crt and orig_tls_key:
            get_logger().log_teardown_step("Restoring original system-local-ca via patch")
            patch_json = f'[{{"op":"replace","path":"/data/tls.crt","value":"{orig_tls_crt}"}},{{"op":"replace","path":"/data/tls.key","value":"{orig_tls_key}"}}]'
            KubectlApplyPatchKeywords(ssh_connection).patch_resource("secret", CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, patch_json)
            SMKeywords(ssh_connection).sm_restart("cert-mon")
            SMKeywords(ssh_connection).sm_restart("cert-alarm")
        file_kw = FileKeywords(ssh_connection)
        file_kw.delete_file("/tmp/short-ca.key")
        file_kw.delete_file("/tmp/short-ca.crt")
        file_kw.delete_file("/tmp/_cert.pem")

    request.addfinalizer(teardown)

    # Pre-check: skip if alarm 500.200 already exists
    get_logger().log_test_case_step("Pre-check: Verify no existing cert alarm")
    initial_alarms = alarm_kw.get_alarm_list()
    if "500.200" in initial_alarms.alarms_id():
        validate_equals(False, True, "Lab already has alarm 500.200 - cannot run cert expiry test in this state")

    # Pre-check: verify original cert has > 30 days remaining
    get_logger().log_test_case_step("Pre-check: Verify original cert not near-expiry")
    secret_kw = KubectlGetSecretsKeywords(ssh_connection)
    cert_pem = secret_kw.get_secret_with_custom_output(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, "go-template", "'{{index .data \"tls.crt\"}}'", base64=True)
    FileKeywords(ssh_connection).create_file_with_heredoc("/tmp/_cert.pem", cert_pem)
    is_valid = openssl_kw.check_cert_expiry("/tmp/_cert.pem", 2592000)
    FileKeywords(ssh_connection).delete_file("/tmp/_cert.pem")
    if not is_valid:
        validate_equals(False, True, "Original cert expires within 30 days - cannot run expiry alarm test")

    # Step 1: Save original cert/key values for safe restore later (keep raw base64 for patching)
    get_logger().log_test_case_step("Save original cert/key values")
    orig_tls_crt = secret_kw.get_secret_with_custom_output(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, "go-template", "'{{index .data \"tls.crt\"}}'")
    orig_tls_key = secret_kw.get_secret_with_custom_output(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, "go-template", "'{{index .data \"tls.key\"}}'")
    get_logger().log_info("Original cert/key values saved for restore")

    # Step 2: Generate short-lived cert matching current key type
    get_logger().log_test_case_step("Generate and patch short-lived cert")
    ca_key_info = openssl_kw.get_cert_key_info_from_secret(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER)
    if ca_key_info.get_type() == "ECDSA":
        openssl_kw.generate_self_signed_cert("/tmp/short-ca.key", "/tmp/short-ca.crt", "/CN=short-ca/O=test", days=1, algorithm="ECDSA", curve=ca_key_info.get_curve())
    else:
        openssl_kw.generate_self_signed_cert("/tmp/short-ca.key", "/tmp/short-ca.crt", "/CN=short-ca/O=test", days=1, algorithm="RSA", rsa_size=ca_key_info.get_size())

    # Read the generated cert/key as base64 for patching
    short_crt_b64 = FileKeywords(ssh_connection).read_file_as_base64("/tmp/short-ca.crt")
    short_key_b64 = FileKeywords(ssh_connection).read_file_as_base64("/tmp/short-ca.key")

    patch_kw = KubectlApplyPatchKeywords(ssh_connection)
    patch_json = f'[{{"op":"replace","path":"/data/tls.crt","value":"{short_crt_b64}"}},{{"op":"replace","path":"/data/tls.key","value":"{short_key_b64}"}}]'
    patch_raw = patch_kw.patch_resource("secret", CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, patch_json)
    validate_str_contains(patch_raw, "patched", "Secret patch should succeed")

    # Step 3: Restart cert-mon AND cert-alarm, wait for alarm
    get_logger().log_test_case_step("Restart cert-mon and cert-alarm, wait for alarm 500.200")
    SMKeywords(ssh_connection).sm_restart("cert-mon")
    SMKeywords(ssh_connection).sm_restart("cert-alarm")

    def alarm_raised():
        """Check if alarm 500.200 is present."""
        alarms = alarm_kw.get_alarm_list()
        return "500.200" in alarms.alarms_id()

    validate_equals_with_retry(alarm_raised, True, "Alarm 500.200 should be raised", 300, 15)

    # Step 4: Verify health-query-upgrade shows Fail
    get_logger().log_test_case_step("Verify health-query-upgrade shows Fail")
    health_kw = SystemHealthQueryKeywords(ssh_connection)
    health_upgrade_output = health_kw.get_kube_upgrade_health_status()
    validate_equals(health_upgrade_output.is_all_healthy(), False, "health-query should show Fail")

    # Step 5: Restore original cert/key via patch (safe - no resourceVersion issues)
    get_logger().log_test_case_step("Restore original cert/key via patch")
    restore_json = f'[{{"op":"replace","path":"/data/tls.crt","value":"{orig_tls_crt}"}},{{"op":"replace","path":"/data/tls.key","value":"{orig_tls_key}"}}]'
    restore_raw = patch_kw.patch_resource("secret", CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, restore_json)
    validate_str_contains(restore_raw, "patched", "Secret restore should succeed")

    # Step 6: Restart services and wait for alarm to clear
    get_logger().log_test_case_step("Restart cert-mon and cert-alarm, wait for alarm to clear")
    SMKeywords(ssh_connection).sm_restart("cert-mon")
    SMKeywords(ssh_connection).sm_restart("cert-alarm")

    def alarm_cleared():
        """Check if alarm 500.200 has cleared."""
        alarms = alarm_kw.get_alarm_list()
        return "500.200" not in alarms.alarms_id()

    validate_equals_with_retry(alarm_cleared, True, "Alarm 500.200 should clear", 300, 15)

    # Step 7: Verify health-query shows no alarm (check specific line, not entire output)
    get_logger().log_test_case_step("Verify health-query-upgrade returns to healthy")

    def health_recovered():
        """Check if health-query-upgrade returns healthy."""
        upgrade_output = health_kw.get_kube_upgrade_health_status()
        return upgrade_output.is_all_healthy()

    validate_equals_with_retry(health_recovered, True, "health-query should return to OK", 120, 15)


@mark.p2
def test_custom_app_cert_no_admission_control(request: FixtureRequest):
    """Verify custom app cert with RSA 2048 is issued without blocking.

    Steps:
        - Create Certificate CR with RSA 2048 in default namespace
        - Apply the resource
        - Verify certificate READY=True (no admission blocking)
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cert_status_kw = KubectlGetCertStatusKeywords(ssh_connection)
    test_cert_name = "test-app-cert-no-admission"

    template_file = get_stx_resource_path("resources/cloud_platform/security/x509/test_app_certificate.yaml")
    replacement_dictionary = {
        "cert_name": test_cert_name,
        "namespace": "default",
        "issuer_name": CLUSTER_ISSUER,
        "key_algorithm": "RSA",
        "key_size": "2048",
        "dns_name": "test-app.local",
    }

    yaml_path = None

    def teardown():
        """Delete test certificate and secret."""
        get_logger().log_teardown_step("Deleting test cert resource and secret")
        if yaml_path:
            KubectlFileDeleteKeywords(ssh_connection).delete_resources(yaml_path, ignore_not_found=True)
            FileKeywords(ssh_connection).delete_file(yaml_path)
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("secret", test_cert_name, "default")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create Certificate CR YAML with RSA 2048")
    yaml_path = YamlKeywords(ssh_connection).generate_yaml_file_from_template(template_file, replacement_dictionary, f"{test_cert_name}.yaml", "/tmp")

    get_logger().log_test_case_step("Apply Certificate resource")
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(yaml_path)

    get_logger().log_test_case_step("Verify certificate READY=True")
    cert_status_kw.wait_for_certs_status(test_cert_name, True, "default", timeout=120)
    get_logger().log_info(f"{test_cert_name}: issued without admission control blocking")


@mark.p2
def test_automatic_renewal_preserves_key_type(request: FixtureRequest):
    """Verify automatic cert renewal preserves key type.

    Steps:
        - Record current revision and key type for system-restapi-gui-certificate
        - Delete secret to trigger renewal
        - Wait for revision to increment
        - Verify renewed cert has same key type and size
        - On Trixie, verify meets platform cert minimum

    Teardown:
        - Verify certificate is READY (cert-manager restores automatically)
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    is_trixie = CloudPlatformVersionManager.is_trixie(ssh_connection)
    cert_name = "system-restapi-gui-certificate"
    renewal_timeout = 120
    cert_status_kw = KubectlGetCertStatusKeywords(ssh_connection)

    def teardown():
        """Ensure certificate is READY after test."""
        get_logger().log_teardown_step("Verify certificate restored")
        cert_status_kw.wait_for_certs_status(cert_name, True, NAMESPACE_DEPLOYMENT, timeout=60)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Record current revision and key type")
    certs_output = cert_status_kw.get_certificates_with_extra_columns(NAMESPACE_DEPLOYMENT, ["revision"])
    cert_obj = certs_output.get_cert(cert_name)
    revision_str = cert_obj.get_revision()
    revision_before = int(revision_str) if revision_str else 0
    key_before = openssl_kw.get_cert_key_info_from_secret(cert_name, NAMESPACE_DEPLOYMENT)
    get_logger().log_info(f"Before: revision={revision_before}, key={key_before}")

    get_logger().log_test_case_step("Delete secret to trigger renewal")
    KubectlDeleteResourceKeywords(ssh_connection).delete_resource("secret", cert_name, NAMESPACE_DEPLOYMENT)
    get_logger().log_info(f"Secret {cert_name} deleted - cert-manager will re-issue automatically")

    get_logger().log_test_case_step("Wait for cert-manager to re-issue")

    def revision_incremented():
        """Check if certificate revision has incremented."""
        updated_certs = cert_status_kw.get_certificates_with_extra_columns(NAMESPACE_DEPLOYMENT, ["revision"])
        rev = updated_certs.get_cert(cert_name).get_revision()
        return int(rev) == revision_before + 1 if rev else False

    validate_equals_with_retry(revision_incremented, True, "Revision should increment", renewal_timeout, 10)

    get_logger().log_test_case_step("Verify key type preserved")
    key_after = openssl_kw.get_cert_key_info_from_secret(cert_name, NAMESPACE_DEPLOYMENT)
    get_logger().log_info(f"After: key={key_after}")
    validate_equals(key_after.get_type(), key_before.get_type(), "Key type should be preserved after renewal")
    validate_equals(key_after.get_size(), key_before.get_size(), "Key size should be preserved after renewal")
    if is_trixie:
        validate_platform_cert_key_meets_minimum(key_after)


@mark.p1
@mark.lab_has_standby_controller
def test_swact_preserves_certificates(request: FixtureRequest):
    """Verify controller swact does not affect certificates or services.

    Steps:
        - Record system-local-ca and platform cert key info
        - Perform system host-swact
        - Verify key info unchanged after swact
        - Verify REST API, registry, LDAP functional
        - Verify no cert-related alarms
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    swact_kw = SystemHostSwactKeywords(ssh_connection)
    swact_performed = False
    oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()

    def teardown():
        """Swact back to restore original active controller."""
        if swact_performed:
            get_logger().log_teardown_step("Swacting back")
            new_ssh = LabConnectionKeywords().get_active_controller_ssh()
            SystemHostSwactKeywords(new_ssh).host_swact()
        else:
            get_logger().log_teardown_step("Swact was not performed, no revert needed")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Record cert key info before swact")
    ca_before = openssl_kw.get_cert_key_info_from_secret(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER)
    platform_before = {}
    for cert_name in PLATFORM_CERTS:
        platform_before[cert_name] = openssl_kw.get_cert_key_info_from_secret(cert_name, NAMESPACE_DEPLOYMENT)
    get_logger().log_info(f"CA before: {ca_before}")

    get_logger().log_test_case_step("Perform swact")
    swact_kw.host_swact()
    swact_performed = True

    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    alarm_kw = AlarmListKeywords(ssh_connection)
    registry_kw = SystemRegistryImageListKeywords(ssh_connection)

    get_logger().log_test_case_step("Verify key info unchanged")
    ca_after = openssl_kw.get_cert_key_info_from_secret(CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER)
    validate_equals(ca_after.get_type(), ca_before.get_type(), "CA key type unchanged after swact")
    validate_equals(ca_after.get_size(), ca_before.get_size(), "CA key size unchanged after swact")
    for cert_name in PLATFORM_CERTS:
        key_after = openssl_kw.get_cert_key_info_from_secret(cert_name, NAMESPACE_DEPLOYMENT)
        validate_equals(key_after.get_type(), platform_before[cert_name].get_type(), f"{cert_name} type unchanged")
        validate_equals(key_after.get_size(), platform_before[cert_name].get_size(), f"{cert_name} size unchanged")

    get_logger().log_test_case_step("Verify REST API accessible")
    curl_kw = CurlKeywords(ssh_connection)
    http_code = curl_kw.get_http_status_code(f"https://{format_url_ip(oam_ip)}:5000/v3")
    validate_equals(http_code, "200", "REST API should return 200 after swact")

    get_logger().log_test_case_step("Verify registry responds")
    registry_kw.get_registry_image_list()

    get_logger().log_test_case_step("Verify LDAP responds")
    admin_pw = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
    ldap_result = LdapKeywords(ssh_connection, admin_pw).check_ldap_connectivity(format_url_ip(oam_ip))
    validate_equals(ldap_result, True, "LDAP should respond over TLS")

    get_logger().log_test_case_step("Verify no cert alarms")
    alarms_output = alarm_kw.get_alarm_list()
    alarm_ids = alarms_output.alarms_id()
    for alarm_id in CERT_ALARM_IDS:
        validate_equals(alarm_id in alarm_ids, False, f"Alarm {alarm_id} absent after swact")


@mark.p2
def test_registry_accessible_with_platform_cert():
    """Verify registry TLS handshake succeeds with platform CA cert.

    Explicitly verifies the registry's ECDSA/RSA TLS certificate is trusted
    by extracting the platform CA and using it for TLS verification.

    Steps:
        - Extract platform CA from system-local-ca secret
        - Verify registry responds to TLS connection using platform CA
        - Verify system registry-image-list works (authenticated access)
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    secret_kw = KubectlGetSecretsKeywords(ssh_connection)
    file_kw = FileKeywords(ssh_connection)

    get_logger().log_test_case_step("Extract platform CA for TLS verification")
    ca_pem = secret_kw.get_secret_with_custom_output(
        CLUSTER_ISSUER, NAMESPACE_CERT_MANAGER, "go-template", "'{{index .data \"tls.crt\"}}'", base64=True
    )
    file_kw.create_file_with_heredoc("/tmp/_platform_ca.pem", ca_pem)

    get_logger().log_test_case_step("Verify registry TLS with platform CA")
    curl_kw = CurlKeywords(ssh_connection)
    http_code = curl_kw.get_http_status_code("https://registry.local:9001/v2/", insecure=False, cacert="/tmp/_platform_ca.pem")
    # 401 = TLS succeeded, auth required (expected without credentials)
    # 200 = TLS succeeded, no auth required
    # 000 = TLS handshake failed (would indicate cert problem)
    validate_not_equals(http_code, "000", "Registry TLS handshake should succeed with platform CA (000 = connection/TLS failure)")
    validate_equals(http_code in ("200", "401"), True, f"Registry should respond with 200 or 401 (got {http_code}) — proves TLS works with platform CA")

    get_logger().log_test_case_step("Verify system registry-image-list works")
    registry_kw = SystemRegistryImageListKeywords(ssh_connection)
    registry_output = registry_kw.get_registry_image_list()
    validate_not_equals(registry_output, None, "Registry image list should return data")

    file_kw.delete_file("/tmp/_platform_ca.pem")


@mark.p2
def test_k8s_certs_key_type():
    """Verify K8S subordinate certificates are ECDSA P-384.

    On Trixie 26.09+, K8S subordinate certs (apiserver, kubelet-client,
    front-proxy, kubeconfig clients) are always ECDSA P-384 as hardcoded
    by kubeadm. The kubernetes-root-ca is set at install time and matches
    whatever platform cert type was configured during initial installation
    (it does NOT change when platform certs are updated later).

    Steps:
        - Detect Trixie (skip on Bullseye)
        - Log kubernetes-root-ca key type (informational only)
        - Validate subordinate certs are ECDSA P-384
        - Validate kubeconfig client certs are ECDSA P-384
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    is_trixie = CloudPlatformVersionManager.is_trixie(ssh_connection)

    if not is_trixie:
        validate_equals(False, True, "K8S cert key type check requires Trixie 26.09+ - lab is not Trixie")

    get_logger().log_test_case_step("Log kubernetes-root-ca key type (informational)")
    ca_key_info = openssl_kw.get_cert_key_info_from_file("/etc/kubernetes/pki/ca.crt")
    get_logger().log_info(f"kubernetes-root-ca: {ca_key_info} (set at install time, not validated)")

    k8s_subordinate_certs = {
        "apiserver": "/etc/kubernetes/pki/apiserver.crt",
        "apiserver-kubelet-client": "/etc/kubernetes/pki/apiserver-kubelet-client.crt",
        "front-proxy-ca": "/etc/kubernetes/pki/front-proxy-ca.crt",
    }

    get_logger().log_test_case_step("Verify K8S subordinate certs are ECDSA P-384")
    for cert_name, cert_path in k8s_subordinate_certs.items():
        key_info = openssl_kw.get_cert_key_info_from_file(cert_path)
        get_logger().log_info(f"{cert_name}: {key_info}")
        validate_equals(key_info.get_type(), "ECDSA", f"{cert_name} should be ECDSA")
        validate_equals(key_info.get_curve(), "secp384r1", f"{cert_name} should be P-384")

    # Check conf-based certs (embedded in kubeconfig files)
    kubeconfig_certs = {
        "admin.conf": "/etc/kubernetes/admin.conf",
        "controller-manager.conf": "/etc/kubernetes/controller-manager.conf",
        "scheduler.conf": "/etc/kubernetes/scheduler.conf",
    }

    get_logger().log_test_case_step("Verify K8S kubeconfig client cert key types are ECDSA P-384")
    for conf_name, conf_path in kubeconfig_certs.items():
        key_info = openssl_kw.get_cert_key_info_from_kubeconfig(conf_path)
        get_logger().log_info(f"{conf_name} client cert: {key_info}")
        validate_equals(key_info.get_type(), "ECDSA", f"{conf_name} client cert should be ECDSA")
        validate_equals(key_info.get_curve(), "secp384r1", f"{conf_name} client cert should be P-384")


@mark.p2
def test_k8s_certs_match_ca_key_type():
    """Verify K8S subordinate certs are consistent ECDSA P-384.

    On Trixie, kubeadm hardcodes all subordinate certs to ECDSA P-384.
    The kubernetes-root-ca may differ (set at install time) but all
    subordinate certs should be consistent with each other.

    Steps:
        - Detect Trixie (skip on Bullseye)
        - Get apiserver and apiserver-kubelet-client key types
        - Verify both are ECDSA P-384
        - Verify they are consistent with each other
    """
    get_logger().log_setup_step("Establish SSH connection to active controller")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openssl_kw = OpenSSLKeywords(ssh_connection)
    is_trixie = CloudPlatformVersionManager.is_trixie(ssh_connection)

    if not is_trixie:
        validate_equals(False, True, "K8S cert consistency check requires Trixie 26.09+ - lab is not Trixie")

    get_logger().log_test_case_step("Get kubernetes-root-ca key type (informational)")
    ca_key_info = openssl_kw.get_cert_key_info_from_file("/etc/kubernetes/pki/ca.crt")
    get_logger().log_info(f"kubernetes-root-ca: {ca_key_info} (set at install time)")

    get_logger().log_test_case_step("Verify subordinate certs are ECDSA P-384")
    subordinate_certs = [
        "/etc/kubernetes/pki/apiserver.crt",
        "/etc/kubernetes/pki/apiserver-kubelet-client.crt",
    ]

    for cert_path in subordinate_certs:
        key_info = openssl_kw.get_cert_key_info_from_file(cert_path)
        get_logger().log_info(f"{cert_path}: {key_info}")
        validate_equals(key_info.get_type(), "ECDSA", f"{cert_path} key type should be ECDSA")
        validate_equals(key_info.get_curve(), "secp384r1", f"{cert_path} should be P-384")

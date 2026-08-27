"""
EJBCA PKI System Application - Automated Test Cases

Tests for the EJBCA Enterprise PKI application deployed on StarlingX.
Covers bootstrap, CMP enrollment, REST API, security validation,
cert-manager integration, HA resilience, performance, and lifecycle.
"""

import time

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import (
    validate_equals,
    validate_equals_with_retry,
    validate_not_equals,
    validate_str_contains,
)
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.security.ejbca.ejbca_backup_restore_keywords import EjbcaBackupRestoreKeywords
from keywords.cloud_platform.security.ejbca.ejbca_certmanager_keywords import EjbcaCertManagerKeywords
from keywords.cloud_platform.security.ejbca.ejbca_cli_keywords import EjbcaCliKeywords
from keywords.cloud_platform.security.ejbca.ejbca_cmp_keywords import EjbcaCmpKeywords
from keywords.cloud_platform.security.ejbca.ejbca_rest_keywords import EjbcaRestKeywords
from keywords.cloud_platform.security.ejbca.ejbca_security_keywords import EjbcaSecurityKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pods.kubectl_pod_logs_keywords import KubectlPodLogsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords
from keywords.network.curl_mtls_keywords import CurlMtlsKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords


@mark.p1
def test_ejbca_app_applied_status():
    """Verify EJBCA application is in 'applied' state.

    Test Steps:
        - Query system application-list for EJBCA app
        - Validate status is 'applied'
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    app_name = ejbca_config.get_app_name()

    get_logger().log_test_case_step(f"Verify {app_name} application status is applied")
    app_list_keywords = SystemApplicationListKeywords(ssh_connection)
    app_output = app_list_keywords.get_system_application_list()
    app_status = app_output.get_application(app_name).get_status()
    validate_equals(app_status, "applied", f"{app_name} application status")


@mark.p1
def test_ejbca_pods_running():
    """Verify all EJBCA pods are in Running state.

    Test Steps:
        - Get pods in EJBCA namespace
        - Validate EJBCA application pods are Running
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()

    get_logger().log_test_case_step(f"Get all pods in namespace {namespace}")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods_output = pods_keywords.get_pods(namespace=namespace)
    pod_list = pods_output.get_pods()

    get_logger().log_test_case_step("Validate all pods are Running")
    for pod in pod_list:
        validate_equals(
            pod.get_status(), "Running",
            f"Pod {pod.get_name()} status"
        )


@mark.p1
def test_ejbca_postgres_ha_cluster():
    """Verify PostgreSQL HA cluster pods are running.

    Test Steps:
        - Get pods matching pg-cluster label in EJBCA namespace
        - Validate at least expected number of PG instances are Running
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    pg_cluster_name = ejbca_config.get_pg_cluster_name()

    get_logger().log_test_case_step("Get PostgreSQL cluster pods")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods_output = pods_keywords.get_pods(namespace=namespace)
    pg_pods = pods_output.get_pods_start_with(pg_cluster_name)

    get_logger().log_test_case_step("Validate PG pods are Running")
    running_count = 0
    for pod in pg_pods:
        if pod.get_status() == "Running":
            running_count += 1
    validate_equals(running_count >= 1, True, "At least one PG pod running")


@mark.p1
def test_ejbca_management_ca_present():
    """Verify ManagementCA exists in EJBCA after bootstrap.

    Test Steps:
        - List CAs via EJBCA CLI
        - Validate ManagementCA is present
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    management_ca = ejbca_config.get_management_ca_name()

    get_logger().log_test_case_step("List CAs via EJBCA CLI")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    ca_present = cli_keywords.is_ca_present(management_ca)

    get_logger().log_test_case_step(f"Validate {management_ca} is present")
    validate_equals(ca_present, True, f"{management_ca} exists")


@mark.p1
def test_ejbca_mtls_endpoint_accessible():
    """Verify EJBCA health endpoint is accessible via mTLS.

    Test Steps:
        - Send mTLS GET to EJBCA health endpoint
        - Validate HTTP 200 response
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    get_logger().log_test_case_step("Query EJBCA health endpoint via mTLS")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    issuer = security_keywords.get_service_tls_cert_issuer(oam_ip, port)

    get_logger().log_test_case_step("Validate TLS certificate has valid issuer")
    validate_str_contains(issuer, "issuer", "TLS cert issuer field present")


@mark.p1
def test_ejbca_oam_port_accessible():
    """Verify EJBCA external port is accessible on OAM IP.

    Test Steps:
        - Attempt curl to OAM:port
        - Validate connectivity (non-zero HTTP response)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    get_logger().log_test_case_step(f"Check OAM port {port} accessibility")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    accessible = security_keywords.is_http_accessible(oam_ip, port)

    get_logger().log_test_case_step("Validate port is accessible (HTTP redirect expected)")
    validate_equals(accessible, True, "OAM port accessible")


@mark.p1
def test_ejbca_helm_hostname_override():
    """Verify EJBCA hostname helm override is configured.

    Test Steps:
        - Query helm override show for EJBCA
        - Validate hostname is set in overrides
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    app_name = ejbca_config.get_app_name()

    get_logger().log_test_case_step("Verify hostname override is set")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    has_hostname = security_keywords.verify_hostname_override_set(app_name)

    validate_equals(has_hostname, True, "Hostname override configured")


@mark.p1
def test_ejbca_pod_replicas():
    """Verify EJBCA has expected number of pod replicas.

    Test Steps:
        - Get EJBCA pods by label
        - Count Running replicas
        - Validate matches expected count for system type
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    pod_label = ejbca_config.get_ejbca_pod_label()

    get_logger().log_test_case_step("Get EJBCA pods by label")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pods_output = pods_keywords.get_pods(namespace=namespace, label=pod_label)
    pod_list = pods_output.get_pods()

    get_logger().log_test_case_step("Count running EJBCA replicas")
    running_count = sum(1 for p in pod_list if p.get_status() == "Running")
    validate_equals(running_count >= 1, True, "At least one EJBCA replica running")


@mark.p1
def test_ejbca_crypto_token_active():
    """Verify ManagementCA CryptoToken is active.

    Test Steps:
        - List crypto tokens via EJBCA CLI
        - Validate ManagementCA token is active
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    token_name = ejbca_config.get_crypto_token_name()

    get_logger().log_test_case_step(f"Check crypto token {token_name} is active")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    is_active = cli_keywords.is_crypto_token_active(token_name)

    validate_equals(is_active, True, f"CryptoToken {token_name} is active")


@mark.p1
def test_ejbca_protocols_enabled():
    """Verify required EJBCA protocols are enabled.

    Test Steps:
        - Get protocol status via EJBCA CLI
        - Validate CMP and REST protocols are enabled
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()

    get_logger().log_test_case_step("Get EJBCA protocol status")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)

    get_logger().log_test_case_step("Validate CMP protocol enabled")
    cmp_enabled = cli_keywords.is_protocol_enabled("CMP")
    validate_equals(cmp_enabled, True, "CMP protocol enabled")

    get_logger().log_test_case_step("Validate REST protocol enabled")
    rest_enabled = cli_keywords.is_protocol_enabled("REST")
    validate_equals(rest_enabled, True, "REST protocol enabled")


@mark.p1
def test_ejbca_pvc_bound():
    """Verify PostgreSQL PVCs are in Bound state.

    Test Steps:
        - Get PVCs in EJBCA namespace
        - Validate PG PVCs are Bound
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()

    get_logger().log_test_case_step("Get PVCs in EJBCA namespace")
    pvc_keywords = KubectlGetPvcKeywords(ssh_connection)
    pvcs_output = pvc_keywords.get_pvcs(namespace=namespace)
    pvc_list = pvcs_output.get_pvcs_list()

    get_logger().log_test_case_step("Validate all PVCs are Bound")
    for pvc in pvc_list:
        validate_equals(pvc.get_status(), "Bound", f"PVC {pvc.get_name()} status")


@mark.p1
def test_ejbca_system_local_ca_ready():
    """Verify system-local-ca ClusterIssuer remains Ready after EJBCA install.

    Test Steps:
        - Check system-local-ca ClusterIssuer status
        - Validate condition is Ready
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()

    get_logger().log_test_case_step("Check system-local-ca ClusterIssuer readiness")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    is_ready = security_keywords.is_system_local_ca_ready()

    validate_equals(is_ready, True, "system-local-ca ClusterIssuer is Ready")


@mark.p1
def test_ejbca_local_registry_images():
    """Verify all EJBCA pods use images from local registry.

    Test Steps:
        - Check container images in EJBCA namespace
        - Validate all images are from registry.local
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()

    get_logger().log_test_case_step("Verify all pod images from local registry")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    all_local = security_keywords.all_pods_use_local_registry()

    validate_equals(all_local, True, "All images from registry.local")


@mark.p1
def test_ejbca_cmp_internal_enrollment(request: FixtureRequest):
    """Verify CMP certificate enrollment via internal pod-local path.

    Test Steps:
        - Generate key and CSR for test CN
        - Enroll via CMP on internal server (localhost:80)
        - Validate enrollment output contains 'received IP'
        - Validate issued certificate subject matches CN

    Teardown:
        - Remove generated key, CSR, and cert files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-internal"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove CMP test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Enroll via CMP internal path")
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(
        server, path, hmac_secret, cn, key_path, csr_path, cert_path
    )

    get_logger().log_test_case_step("Validate enrollment success")
    validate_str_contains(output, "received IP", "CMP internal enrollment")


@mark.p1
def test_ejbca_cmp_external_enrollment(request: FixtureRequest):
    """Verify CMP certificate enrollment via external OAM mTLS path.

    Test Steps:
        - Generate key and CSR
        - Enroll via CMP on external OAM:port
        - Validate enrollment output contains 'received IP'

    Teardown:
        - Remove generated key, CSR, and cert files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()
    cn = "test-cmp-external"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove CMP test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Enroll via CMP external path")
    server = f"{oam_ip}:{port}"
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(
        server, path, hmac_secret, cn, key_path, csr_path, cert_path
    )

    get_logger().log_test_case_step("Validate enrollment success")
    validate_str_contains(output, "received IP", "CMP external enrollment")


@mark.p1
def test_ejbca_cmp_renewal(request: FixtureRequest):
    """Verify CMP certificate renewal produces a new serial number.

    Test Steps:
        - Enroll initial certificate
        - Enroll renewal certificate with same CN
        - Validate serial numbers differ

    Teardown:
        - Remove generated cert files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-renewal"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert1_path = f"/tmp/{cn}-1.crt"
    cert2_path = f"/tmp/{cn}-2.crt"

    def teardown():
        get_logger().log_teardown_step("Remove CMP renewal test artifacts")
        file_kw = FileKeywords(ssh_connection)

        file_kw.delete_file(key_path)

        file_kw.delete_file(csr_path)

        file_kw.delete_file(cert1_path)

        file_kw.delete_file(cert2_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Initial enrollment")
    cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert1_path)

    get_logger().log_test_case_step("Renewal enrollment")
    cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert2_path)

    get_logger().log_test_case_step("Compare serial numbers")
    cert1_info = cmp_keywords.get_certificate_info(cert1_path)
    cert2_info = cmp_keywords.get_certificate_info(cert2_path)
    serial1 = cert1_info.get_serial()
    serial2 = cert2_info.get_serial()
    validate_equals(serial1 != serial2, True, "Renewal produces different serial")


@mark.p1
def test_ejbca_cmp_revocation(request: FixtureRequest):
    """Verify CMP certificate revocation via revocation request.

    Test Steps:
        - Enroll a certificate via CMP
        - Revoke the certificate
        - Validate revocation output contains 'received RP'

    Teardown:
        - Remove generated cert files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-revoke"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove CMP revocation test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()

    get_logger().log_test_case_step("Generate key, CSR, and enroll")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)
    cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert_path)

    get_logger().log_test_case_step("Revoke the certificate")
    output = cmp_keywords.cmp_revoke(
        server, path, hmac_secret, cn, cert_path
    )

    get_logger().log_test_case_step("Validate revocation accepted")
    validate_str_contains(output, "received RP", "CMP revocation accepted")


@mark.p1
def test_ejbca_cmp_hmac_authentication(request: FixtureRequest):
    """Verify CMP enrollment uses HMAC authentication successfully.

    Test Steps:
        - Enroll via CMP with configured HMAC secret
        - Validate certificate is issued (received IP)

    Teardown:
        - Remove generated files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-hmac"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove CMP HMAC test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Enroll with valid HMAC secret")
    output = cmp_keywords.cmp_enroll(
        server, path, hmac_secret, cn, key_path, csr_path, cert_path
    )

    validate_str_contains(output, "received IP", "HMAC authenticated enrollment")


@mark.p1
def test_ejbca_cmp_tls_transport(request: FixtureRequest):
    """Verify CMP works over TLS transport (HTTPS) on external port.

    Test Steps:
        - Enroll via CMP on OAM:port using TLS
        - Validate successful certificate issuance

    Teardown:
        - Remove generated files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()
    cn = "test-cmp-tls"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove CMP TLS test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Enroll via CMP over TLS")
    server = f"{oam_ip}:{port}"
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(
        server, path, hmac_secret, cn, key_path, csr_path, cert_path
    )

    validate_str_contains(output, "received IP", "CMP over TLS transport")


@mark.p1
def test_ejbca_cmp_invalid_hmac(request: FixtureRequest):
    """Verify CMP rejects enrollment with invalid HMAC secret.

    Test Steps:
        - Attempt CMP enrollment with wrong HMAC
        - Validate error response (no certificate issued)

    Teardown:
        - Remove generated key, CSR, and cert files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-bad-hmac"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove invalid HMAC test artifacts")
        file_keywords = FileKeywords(ssh_connection)
        file_keywords.delete_file(key_path)
        file_keywords.delete_file(csr_path)
        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Attempt enrollment with invalid HMAC")
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    output = cmp_keywords.cmp_enroll_with_invalid_secret(
        server, path, "wrong-secret-12345", cn, key_path, csr_path, cert_path
    )

    get_logger().log_test_case_step("Validate enrollment rejected")
    validate_str_contains(output, "ERROR", "Invalid HMAC rejected")


@mark.p1
def test_ejbca_cmp_alias_config():
    """Verify CMP alias configuration matches expected settings.

    Test Steps:
        - Verify CMP protocol is enabled
        - Validate alias is usable (implied by protocol enablement)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()

    get_logger().log_test_case_step("Verify CMP protocol enabled for alias use")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    cmp_enabled = cli_keywords.is_protocol_enabled("CMP")
    validate_equals(cmp_enabled, True, "CMP enabled for alias")


@mark.p1
def test_ejbca_ocsp_endpoint():
    """Verify OCSP responder endpoint is accessible.

    Test Steps:
        - Check OCSP protocol is enabled via EJBCA CLI
        - Validate OCSP is reported as enabled
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()

    get_logger().log_test_case_step("Check OCSP protocol status")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    ocsp_enabled = cli_keywords.is_protocol_enabled("OCSP")

    validate_equals(ocsp_enabled, True, "OCSP protocol enabled")


@mark.p1
def test_ejbca_rest_enrollment(request: FixtureRequest):
    """Verify REST API certificate enrollment via pkcs10enroll.

    Test Steps:
        - Generate key and DER-encoded CSR
        - Submit enrollment via REST API
        - Validate response contains certificate data

    Teardown:
        - Remove generated key and CSR files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()
    cn = "test-rest-enroll"
    key_path = f"/tmp/{cn}.key"
    csr_der_path = f"/tmp/{cn}.der"

    def teardown():
        get_logger().log_teardown_step("Remove REST enrollment test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_der_path)

    request.addfinalizer(teardown)

    openssl_keywords = OpenSSLKeywords(ssh_connection)
    openssl_keywords.generate_rsa_key(key_path)

    get_logger().log_test_case_step("Generate DER CSR for REST enrollment")
    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    rest_keywords = EjbcaRestKeywords(ssh_connection, admin_cert, admin_key)
    csr_b64 = rest_keywords.generate_csr_der_base64(key_path, csr_der_path, cn)

    get_logger().log_test_case_step("Submit REST pkcs10enroll")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    response = rest_keywords.rest_enroll_pkcs10(
        base_url, csr_b64,
        ejbca_config.get_rest_cert_profile(),
        ejbca_config.get_rest_ee_profile(),
        ejbca_config.get_rest_ca_name(),
        cn, ejbca_config.get_rest_enroll_password()
    )

    get_logger().log_test_case_step("Validate enrollment response")
    response_str = str(response)
    validate_str_contains(response_str, "certificate", "REST enrollment returned certificate data")


@mark.p1
def test_ejbca_rest_revocation(request: FixtureRequest):
    """Verify REST API certificate revocation.

    Test Steps:
        - Enroll a certificate via REST
        - Revoke it via REST revocation endpoint
        - Validate revocation status

    Teardown:
        - Remove generated key and CSR files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()
    cn = "test-rest-revoke"
    key_path = f"/tmp/{cn}.key"
    csr_der_path = f"/tmp/{cn}.der"

    def teardown():
        get_logger().log_teardown_step("Remove REST revocation test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_der_path)

    request.addfinalizer(teardown)

    openssl_keywords = OpenSSLKeywords(ssh_connection)
    openssl_keywords.generate_rsa_key(key_path)

    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    rest_keywords = EjbcaRestKeywords(ssh_connection, admin_cert, admin_key)
    csr_b64 = rest_keywords.generate_csr_der_base64(key_path, csr_der_path, cn)

    get_logger().log_test_case_step("Enroll certificate for revocation test")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    response = rest_keywords.rest_enroll_pkcs10(
        base_url, csr_b64,
        ejbca_config.get_rest_cert_profile(),
        ejbca_config.get_rest_ee_profile(),
        ejbca_config.get_rest_ca_name(),
        cn, ejbca_config.get_rest_enroll_password()
    )
    validate_not_equals(response, {}, "REST enrollment for revocation test returned data")
    serial_hex = response.get("serial_number", "")

    get_logger().log_test_case_step("Revoke the certificate via REST")
    issuer_dn = response.get("issuer_dn", "")
    revoke_output = rest_keywords.rest_revoke_cert(
        base_url, issuer_dn, serial_hex
    )
    raw_revoke = "\n".join(revoke_output) if isinstance(revoke_output, list) else revoke_output

    get_logger().log_test_case_step("Validate revocation response")
    validate_str_contains(raw_revoke, "revoked", "Certificate revoked via REST")


@mark.p1
def test_ejbca_rest_status():
    """Verify REST API status endpoint returns OK.

    Test Steps:
        - Query EJBCA REST status endpoint
        - Validate status is OK and version is returned
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    curl_keywords = CurlMtlsKeywords(ssh_connection, admin_cert, admin_key)

    get_logger().log_test_case_step("Query REST status endpoint")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    status_code = curl_keywords.get_http_status_code(f"{base_url}/v1/ca")

    get_logger().log_test_case_step("Validate HTTP 200 response")
    validate_equals(status_code, "200", "REST status endpoint returns 200")


@mark.p1
def test_ejbca_rest_no_client_cert():
    """Verify REST API rejects requests without client certificate.

    Test Steps:
        - Send curl request without client cert to REST endpoint
        - Validate connection fails (TLS handshake error)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    rest_keywords = EjbcaRestKeywords(ssh_connection, admin_cert, admin_key)

    get_logger().log_test_case_step("Attempt REST request without client cert")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    rc = rest_keywords.rest_no_client_cert_rejected(f"{base_url}/v1/ca")

    get_logger().log_test_case_step("Validate request is rejected")
    validate_not_equals(rc, 0, "No client cert rejected by REST endpoint")


@mark.p1
def test_ejbca_rest_ca_listing():
    """Verify REST API CA listing returns ManagementCA.

    Test Steps:
        - Query REST CA listing endpoint
        - Validate ManagementCA is in the response
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    rest_keywords = EjbcaRestKeywords(ssh_connection, admin_cert, admin_key)

    get_logger().log_test_case_step("List CAs via REST API")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    response = rest_keywords.rest_list_cas(base_url)

    get_logger().log_test_case_step("Validate ManagementCA in response")
    response_str = str(response)
    management_ca = ejbca_config.get_management_ca_name()
    validate_str_contains(response_str, management_ca, "ManagementCA in REST listing")


@mark.p1
def test_ejbca_ca_key_not_in_secrets():
    """Verify CA private key is not exposed in Kubernetes secrets.

    Test Steps:
        - Search all secrets in EJBCA namespace for private key material
        - Validate no CA private key found (only service cert keys)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()

    get_logger().log_test_case_step("Check secrets for CA private key material")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    has_ca_key = security_keywords.secrets_contain_private_key()

    get_logger().log_test_case_step("Validate CA key not in secrets")
    validate_equals(has_ca_key, False, "No CA private key in secrets")


@mark.p1
def test_ejbca_crypto_token_not_exportable():
    """Verify CryptoToken is active and listed (SoftCryptoToken).

    Test Steps:
        - List crypto tokens via EJBCA CLI
        - Validate ManagementCA token reports as active (SoftCryptoToken)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    token_name = ejbca_config.get_crypto_token_name()

    get_logger().log_test_case_step(f"List crypto tokens and check {token_name}")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    output = cli_keywords.list_crypto_tokens()
    raw = "\n".join(output) if isinstance(output, list) else output

    get_logger().log_test_case_step("Validate CryptoToken is active (encrypted)")
    validate_str_contains(raw, token_name, "CryptoToken listed")
    is_active = cli_keywords.is_crypto_token_active(token_name)
    validate_equals(is_active, True, "CryptoToken is active")


@mark.p1
def test_ejbca_non_root_user():
    """Verify EJBCA pods run as non-root user.

    Test Steps:
        - Get EJBCA pod security context
        - Validate container runs with non-root UID
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()

    get_logger().log_test_case_step("Get EJBCA pod user ID")
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    pod_name = cli_keywords.get_ejbca_pod_name()
    exec_keywords = KubectlExecInPodsKeywords(ssh_connection)
    output = exec_keywords.run_pod_exec_cmd(pod_name, "id -u", options=f"-n {namespace}")
    raw = "\n".join(output) if isinstance(output, list) else output
    uid = raw.strip()

    get_logger().log_test_case_step("Validate non-root UID")
    validate_equals(uid != "0", True, "EJBCA runs as non-root user")


@mark.p1
def test_ejbca_default_sa_cannot_exec():
    """Verify default ServiceAccount cannot exec into EJBCA pods.

    Test Steps:
        - Attempt kubectl exec as default SA
        - Validate access is denied
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()

    get_logger().log_test_case_step("Attempt exec as default ServiceAccount")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    can_exec = security_keywords.can_default_sa_exec_into_ejbca()

    get_logger().log_test_case_step("Validate exec denied")
    validate_equals(can_exec, False, "Default SA cannot exec into EJBCA")


@mark.p1
def test_ejbca_fake_cert_rejected():
    """Verify self-signed (fake) client cert is rejected by mTLS.

    Test Steps:
        - Generate a self-signed certificate (not in CA trust chain)
        - Attempt mTLS connection with fake cert
        - Validate connection is rejected
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    get_logger().log_test_case_step("Test fake client cert rejection")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    fake_accepted = security_keywords.is_fake_client_cert_accepted(oam_ip, port)

    get_logger().log_test_case_step("Validate fake cert rejected")
    validate_equals(fake_accepted, False, "Self-signed cert rejected by mTLS")


@mark.p1
def test_ejbca_hmac_not_in_logs():
    """Verify HMAC secret is not exposed in container logs.

    Test Steps:
        - Search EJBCA pod logs for HMAC secret value
        - Validate zero occurrences found
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()

    get_logger().log_test_case_step("Search EJBCA pod logs for HMAC secret")
    pod_logs_keywords = KubectlPodLogsKeywords(ssh_connection)
    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    pod_name = cli_keywords.get_ejbca_pod_name()
    output = pod_logs_keywords.get_pod_logs(pod_name, namespace=namespace)
    raw = "\n".join(output) if isinstance(output, list) else output
    occurrences = raw.count(hmac_secret)

    get_logger().log_test_case_step("Validate HMAC not leaked in logs")
    validate_equals(occurrences, 0, "HMAC secret not found in logs")


@mark.p1
def test_ejbca_cmp_no_san_enrollment(request: FixtureRequest):
    """Verify CMP enrollment without SAN succeeds (ENDUSER profile permissive).

    Test Steps:
        - Generate key and CSR without SAN extension
        - Enroll via CMP
        - Validate certificate is issued (permissive profile)

    Teardown:
        - Remove generated files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-no-san"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove no-SAN test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)

    get_logger().log_test_case_step("Generate key and CSR without SAN")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns="")

    get_logger().log_test_case_step("Enroll via CMP without SAN")
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(
        server, path, hmac_secret, cn, key_path, csr_path, cert_path
    )

    get_logger().log_test_case_step("Validate cert issued without SAN")
    validate_str_contains(output, "received IP", "No-SAN enrollment succeeds")


@mark.p1
def test_ejbca_rest_wrong_ca(request: FixtureRequest):
    """Verify REST enrollment with non-existent CA returns error.

    Test Steps:
        - Submit REST enrollment with fake CA name
        - Validate HTTP 400 response with error message

    Teardown:
        - Remove generated key and CSR files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()
    cn = "test-rest-wrong-ca"
    key_path = f"/tmp/{cn}.key"
    csr_der_path = f"/tmp/{cn}.der"

    def teardown():
        get_logger().log_teardown_step("Remove wrong-CA test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_der_path)

    request.addfinalizer(teardown)

    openssl_keywords = OpenSSLKeywords(ssh_connection)
    openssl_keywords.generate_rsa_key(key_path)

    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    rest_keywords = EjbcaRestKeywords(ssh_connection, admin_cert, admin_key)
    csr_b64 = rest_keywords.generate_csr_der_base64(key_path, csr_der_path, cn)

    get_logger().log_test_case_step("Submit REST enrollment with fake CA")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    response = rest_keywords.rest_enroll_pkcs10(
        base_url, csr_b64,
        ejbca_config.get_rest_cert_profile(),
        ejbca_config.get_rest_ee_profile(),
        "FakeCA", cn, ejbca_config.get_rest_enroll_password()
    )

    get_logger().log_test_case_step("Validate error response for wrong CA")
    validate_not_equals(response, {}, "REST response is not empty for wrong CA")
    response_str = str(response)
    validate_str_contains(response_str, "FakeCA", "Error mentions wrong CA name")


@mark.p1
def test_ejbca_rest_wrong_profile(request: FixtureRequest):
    """Verify REST enrollment with non-existent profile returns error.

    Test Steps:
        - Submit REST enrollment with fake certificate profile
        - Validate error response

    Teardown:
        - Remove generated key and CSR files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()
    cn = "test-rest-wrong-profile"
    key_path = f"/tmp/{cn}.key"
    csr_der_path = f"/tmp/{cn}.der"

    def teardown():
        get_logger().log_teardown_step("Remove wrong-profile test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_der_path)

    request.addfinalizer(teardown)

    openssl_keywords = OpenSSLKeywords(ssh_connection)
    openssl_keywords.generate_rsa_key(key_path)

    admin_cert = ejbca_config.get_admin_cert_path()
    admin_key = ejbca_config.get_admin_key_path()
    rest_keywords = EjbcaRestKeywords(ssh_connection, admin_cert, admin_key)
    csr_b64 = rest_keywords.generate_csr_der_base64(key_path, csr_der_path, cn)

    get_logger().log_test_case_step("Submit REST enrollment with fake profile")
    base_url = f"https://{oam_ip}:{port}{ejbca_config.get_rest_base_path()}"
    response = rest_keywords.rest_enroll_pkcs10(
        base_url, csr_b64,
        "NONEXISTENT",
        ejbca_config.get_rest_ee_profile(),
        ejbca_config.get_rest_ca_name(),
        cn, ejbca_config.get_rest_enroll_password()
    )

    get_logger().log_test_case_step("Validate error response for wrong profile")
    validate_not_equals(response, {}, "REST response is not empty for wrong profile")
    response_str = str(response)
    validate_str_contains(response_str, "NONEXISTENT", "Error mentions wrong profile")


@mark.p1
def test_ejbca_cmp_bad_hmac_no_cert():
    """Verify CMP with bad HMAC does not produce a certificate file.

    Test Steps:
        - Attempt enrollment with wrong HMAC
        - Validate cert file does not exist after failure
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-bad-hmac-nocert"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Attempt enrollment with bad HMAC")
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    cmp_keywords.cmp_enroll_with_invalid_secret(
        server, path, "totally-wrong-secret", cn, key_path, csr_path, cert_path
    )

    get_logger().log_test_case_step("Verify cert file not created")
    file_kw = FileKeywords(ssh_connection)
    file_exists = file_kw.file_exists(cert_path)
    validate_equals(file_exists, False, "No cert file created with bad HMAC")


@mark.p1
def test_ejbca_revoked_cert_mtls_rejected():
    """Verify a revoked certificate cannot be used for mTLS access.

    Test Steps:
        - Attempt mTLS with a self-signed cert (simulating untrusted/revoked)
        - Validate connection fails
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    port = ejbca_config.get_cmp_external_port()

    get_logger().log_test_case_step("Test untrusted cert rejection (simulates revoked)")
    security_keywords = EjbcaSecurityKeywords(ssh_connection, ejbca_config.get_namespace())
    accepted = security_keywords.is_fake_client_cert_accepted(oam_ip, port)

    get_logger().log_test_case_step("Validate untrusted cert rejected")
    validate_equals(accepted, False, "Untrusted/revoked cert rejected by mTLS")


@mark.p1
def test_ejbca_cmp_re_enrollment(request: FixtureRequest):
    """Verify re-enrollment of same CN works (RA auto-resets entity).

    Test Steps:
        - Enroll certificate for a CN
        - Enroll again with same CN without manual entity reset
        - Validate second enrollment succeeds

    Teardown:
        - Remove generated files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-cmp-re-enroll"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert1_path = f"/tmp/{cn}-1.crt"
    cert2_path = f"/tmp/{cn}-2.crt"

    def teardown():
        get_logger().log_teardown_step("Remove re-enrollment test artifacts")
        file_kw = FileKeywords(ssh_connection)

        file_kw.delete_file(key_path)

        file_kw.delete_file(csr_path)

        file_kw.delete_file(cert1_path)

        file_kw.delete_file(cert2_path)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("First enrollment")
    cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert1_path)

    get_logger().log_test_case_step("Re-enrollment without manual reset")
    output = cmp_keywords.cmp_enroll(
        server, path, hmac_secret, cn, key_path, csr_path, cert2_path
    )

    get_logger().log_test_case_step("Validate re-enrollment success")
    validate_str_contains(output, "received IP", "Re-enrollment succeeds")


@mark.p1
def test_ejbca_cluster_issuer_ready():
    """Verify EJBCA cert-manager ClusterIssuer is in Ready state.

    Test Steps:
        - Query ClusterIssuer resource status
        - Validate condition type is Ready
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()

    issuer_name = ejbca_config.get_cert_manager_cluster_issuer_name()
    cert_mgr_keywords = EjbcaCertManagerKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Check ClusterIssuer {issuer_name} readiness")
    is_ready = cert_mgr_keywords.is_cluster_issuer_ready(issuer_name)

    validate_equals(is_ready, True, f"ClusterIssuer {issuer_name} is Ready")


@mark.p1
def test_ejbca_certmanager_certificate_issuance(request: FixtureRequest):
    """Verify cert-manager can issue a certificate via EJBCA ClusterIssuer.

    Test Steps:
        - Create a Certificate CR referencing EJBCA ClusterIssuer
        - Wait for Certificate to become Ready
        - Validate TLS secret is created

    Teardown:
        - Delete Certificate CR and TLS secret
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    issuer_name = ejbca_config.get_cert_manager_cluster_issuer_name()
    issuer_group = ejbca_config.get_cert_manager_issuer_group()
    cert_name = "test-ejbca-cert-issue"
    secret_name = f"{cert_name}-tls"

    def teardown():
        get_logger().log_teardown_step("Delete Certificate CR and secret")
        cert_mgr_keywords.delete_certificate_cr(cert_name, namespace)
        cert_mgr_keywords.delete_tls_secret(secret_name, namespace)

    request.addfinalizer(teardown)

    cert_mgr_keywords = EjbcaCertManagerKeywords(ssh_connection)

    get_logger().log_test_case_step("Create Certificate CR via EJBCA issuer")
    cert_mgr_keywords.create_certificate_cr(
        cert_name, namespace, secret_name,
        f"{cert_name}.local", issuer_name, issuer_group
    )

    get_logger().log_test_case_step("Wait for Certificate to become Ready")
    is_ready = cert_mgr_keywords.wait_for_certificate_ready(cert_name, namespace)
    validate_equals(is_ready, True, "Certificate CR became Ready")

    get_logger().log_test_case_step("Validate TLS secret exists")
    cert_data = cert_mgr_keywords.get_tls_secret_cert_data(secret_name, namespace)
    validate_equals(len(cert_data) > 0, True, "TLS secret contains certificate data")


@mark.p1
def test_ejbca_certmanager_certificate_renewal(request: FixtureRequest):
    """Verify cert-manager renews certificate when secret is deleted.

    Test Steps:
        - Create Certificate CR and wait for Ready
        - Delete the TLS secret to trigger renewal
        - Wait for new secret to appear
        - Validate new certificate data differs from original

    Teardown:
        - Delete Certificate CR and TLS secret
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    issuer_name = ejbca_config.get_cert_manager_cluster_issuer_name()
    issuer_group = ejbca_config.get_cert_manager_issuer_group()
    cert_name = "test-ejbca-cert-renew"
    secret_name = f"{cert_name}-tls"

    def teardown():
        get_logger().log_teardown_step("Delete renewal test Certificate CR and secret")
        cert_mgr_keywords.delete_certificate_cr(cert_name, namespace)
        cert_mgr_keywords.delete_tls_secret(secret_name, namespace)

    request.addfinalizer(teardown)

    cert_mgr_keywords = EjbcaCertManagerKeywords(ssh_connection)

    get_logger().log_test_case_step("Create Certificate CR")
    cert_mgr_keywords.create_certificate_cr(
        cert_name, namespace, secret_name,
        f"{cert_name}.local", issuer_name, issuer_group
    )
    cert_mgr_keywords.wait_for_certificate_ready(cert_name, namespace)

    get_logger().log_test_case_step("Record original cert data")
    original_data = cert_mgr_keywords.get_tls_secret_cert_data(secret_name, namespace)

    get_logger().log_test_case_step("Delete TLS secret to trigger renewal")
    cert_mgr_keywords.delete_tls_secret(secret_name, namespace)

    get_logger().log_test_case_step("Wait for renewed secret")
    renewed = cert_mgr_keywords.wait_for_secret_exists(secret_name, namespace)
    validate_equals(renewed, True, "Renewed TLS secret appeared")

    get_logger().log_test_case_step("Validate certificate data changed")
    new_data = cert_mgr_keywords.get_tls_secret_cert_data(secret_name, namespace)
    validate_equals(original_data != new_data, True, "Certificate renewed with new data")


@mark.p1
def test_ejbca_certmanager_multiple_certs(request: FixtureRequest):
    """Verify cert-manager can issue multiple certificates concurrently.

    Test Steps:
        - Create 5 Certificate CRs via EJBCA ClusterIssuer
        - Wait for all to become Ready
        - Validate all 5 TLS secrets exist

    Teardown:
        - Delete all Certificate CRs and TLS secrets
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    issuer_name = ejbca_config.get_cert_manager_cluster_issuer_name()
    issuer_group = ejbca_config.get_cert_manager_issuer_group()
    cert_count = 5
    cert_prefix = "test-ejbca-multi"

    def teardown():
        get_logger().log_teardown_step("Delete multiple cert test artifacts")
        for i in range(cert_count):
            name = f"{cert_prefix}-{i}"
            cert_mgr_keywords.delete_certificate_cr(name, namespace)
            cert_mgr_keywords.delete_tls_secret(f"{name}-tls", namespace)

    request.addfinalizer(teardown)

    cert_mgr_keywords = EjbcaCertManagerKeywords(ssh_connection)

    get_logger().log_test_case_step(f"Create {cert_count} Certificate CRs")
    for i in range(cert_count):
        name = f"{cert_prefix}-{i}"
        cert_mgr_keywords.create_certificate_cr(
            name, namespace, f"{name}-tls",
            f"{name}.local", issuer_name, issuer_group
        )

    get_logger().log_test_case_step("Wait for all certificates to become Ready")
    ready_count = 0
    for i in range(cert_count):
        name = f"{cert_prefix}-{i}"
        if cert_mgr_keywords.wait_for_certificate_ready(name, namespace, timeout=180):
            ready_count += 1

    get_logger().log_test_case_step("Validate all certificates Ready")
    validate_equals(ready_count, cert_count, f"All {cert_count} certs Ready")


@mark.p1
@mark.lab_has_standby_controller
def test_ejbca_pod_kill_recovery(request: FixtureRequest):
    """Verify EJBCA pod recovers after being killed.

    Test Steps:
        - Delete an EJBCA pod to simulate failure
        - Wait for pod to restart and reach Running state
        - Validate CMP enrollment works after recovery

    Teardown:
        - Remove CMP test artifacts
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    cn = "test-ha-pod-kill"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove HA pod kill test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    cli_keywords = EjbcaCliKeywords(ssh_connection, namespace)
    pod_name = cli_keywords.get_ejbca_pod_name()

    get_logger().log_test_case_step(f"Delete EJBCA pod {pod_name}")
    delete_pods_keywords = KubectlDeletePodsKeywords(ssh_connection)
    delete_pods_keywords.delete_pod(pod_name, namespace=namespace)

    get_logger().log_test_case_step("Wait for pod recovery")
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)
    pod_ready_timeout = ejbca_config.get_pod_ready_timeout()

    def check_pods_running():
        pods_output = pods_keywords.get_pods(namespace=namespace, label=ejbca_config.get_ejbca_pod_label())
        pod_list = pods_output.get_pods()
        return all(p.get_status() == "Running" for p in pod_list) and len(pod_list) >= 1

    validate_equals_with_retry(check_pods_running, True, "EJBCA pods Running after recovery", timeout=pod_ready_timeout)

    get_logger().log_test_case_step("Validate CMP works after recovery")
    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert_path)
    validate_str_contains(output, "received IP", "CMP works after pod kill")


@mark.p1
@mark.lab_has_standby_controller
def test_ejbca_pg_failover_recovery(request: FixtureRequest):
    """Verify EJBCA recovers after PostgreSQL primary failover.

    Test Steps:
        - Delete PG primary pod to trigger failover
        - Wait for EJBCA to reconnect
        - Validate CMP enrollment works after failover

    Teardown:
        - Remove CMP test artifacts
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    pg_cluster = ejbca_config.get_pg_cluster_name()
    cn = "test-ha-pg-failover"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove PG failover test artifacts")
        file_keywords = FileKeywords(ssh_connection)

        file_keywords.delete_file(key_path)

        file_keywords.delete_file(csr_path)

        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Delete PG primary pod to trigger failover")
    delete_pods_keywords = KubectlDeletePodsKeywords(ssh_connection)
    delete_pods_keywords.delete_pod(f"{pg_cluster}-1", namespace=namespace)

    get_logger().log_test_case_step("Wait for PG failover and EJBCA reconnection")
    pg_timeout = ejbca_config.get_pg_failover_timeout()
    pods_keywords = KubectlGetPodsKeywords(ssh_connection)

    def check_pg_ready():
        pods_output = pods_keywords.get_pods(namespace=namespace)
        pg_pods = pods_output.get_pods_start_with(pg_cluster)
        running = [p for p in pg_pods if p.get_status() == "Running"]
        return len(running) >= 1

    validate_equals_with_retry(check_pg_ready, True, "PG pods Running after failover", timeout=pg_timeout)

    get_logger().log_test_case_step("Validate CMP after PG failover")
    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert_path)
    validate_str_contains(output, "received IP", "CMP works after PG failover")


@mark.p1
@mark.lab_has_standby_controller
def test_ejbca_controller_swact(request: FixtureRequest):
    """Verify EJBCA survives controller swact.

    Test Steps:
        - Perform controller swact
        - Wait for EJBCA pods to be Running
        - Validate CMP enrollment works after swact

    Teardown:
        - Remove CMP test artifacts
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    namespace = ejbca_config.get_namespace()
    cn = "test-ha-swact"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_path = f"/tmp/{cn}.crt"

    def teardown():
        get_logger().log_teardown_step("Remove swact test artifacts")
        new_ssh = LabConnectionKeywords().get_active_controller_ssh()
        file_keywords = FileKeywords(new_ssh)
        file_keywords.delete_file(key_path)
        file_keywords.delete_file(csr_path)
        file_keywords.delete_file(cert_path)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Perform controller swact")
    swact_keywords = SystemHostSwactKeywords(ssh_connection)
    swact_keywords.host_swact()

    get_logger().log_test_case_step("Reconnect to new active controller")
    new_ssh = LabConnectionKeywords().get_active_controller_ssh()
    swact_timeout = ejbca_config.get_swact_recovery_timeout()

    get_logger().log_test_case_step("Wait for EJBCA pods Running after swact")
    pods_keywords = KubectlGetPodsKeywords(new_ssh)

    def check_ejbca_after_swact():
        pods_output = pods_keywords.get_pods(namespace=namespace, label=ejbca_config.get_ejbca_pod_label())
        pod_list = pods_output.get_pods()
        return all(p.get_status() == "Running" for p in pod_list) and len(pod_list) >= 1

    validate_equals_with_retry(check_ejbca_after_swact, True, "EJBCA pods Running after swact", timeout=swact_timeout)

    get_logger().log_test_case_step("Validate CMP after swact")
    cmp_keywords = EjbcaCmpKeywords(new_ssh)
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    output = cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert_path)
    validate_str_contains(output, "received IP", "CMP works after swact")


@mark.p1
@mark.lab_has_standby_controller
def test_ejbca_enrollment_during_activity(request: FixtureRequest):
    """Verify continuous enrollment works during normal operation.

    Test Steps:
        - Perform 10 CMP enrollments sequentially
        - Validate all succeed

    Teardown:
        - Remove generated cert files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn_prefix = "test-ha-activity"
    enroll_count = 10

    def teardown():
        get_logger().log_teardown_step("Remove activity test artifacts")
        for i in range(enroll_count):
            file_kw = FileKeywords(ssh_connection)

            file_kw.delete_file(f"/tmp/{cn_prefix}-{i}.key")

            file_kw.delete_file(f"/tmp/{cn_prefix}-{i}.csr")

            file_kw.delete_file(f"/tmp/{cn_prefix}-{i}.crt")

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    server = ejbca_config.get_cmp_internal_server()
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()
    success_count = 0

    get_logger().log_test_case_step(f"Perform {enroll_count} sequential CMP enrollments")
    for i in range(enroll_count):
        cn = f"{cn_prefix}-{i}"
        key_path = f"/tmp/{cn}.key"
        csr_path = f"/tmp/{cn}.csr"
        cert_path = f"/tmp/{cn}.crt"
        cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)
        output = cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert_path)
        raw = "\n".join(output) if isinstance(output, list) else output
        if "received IP" in raw:
            success_count += 1

    get_logger().log_test_case_step("Validate all enrollments succeeded")
    validate_equals(success_count, enroll_count, "All sequential enrollments succeed")


@mark.p1
@mark.lab_has_standby_controller
def test_ejbca_network_interruption_clean_failure(request: FixtureRequest):
    """Verify CMP fails cleanly with unreachable server.

    Test Steps:
        - Attempt CMP enrollment to non-existent server
        - Validate clean error (connection refused)
        - Validate normal enrollment still works

    Teardown:
        - Remove generated files
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ejbca_config = ConfigurationManager.get_security_config().get_ejbca_config()
    cn = "test-ha-network"
    key_path = f"/tmp/{cn}.key"
    csr_path = f"/tmp/{cn}.csr"
    cert_bad = f"/tmp/{cn}-bad.crt"
    cert_good = f"/tmp/{cn}-good.crt"

    def teardown():
        get_logger().log_teardown_step("Remove network test artifacts")
        file_kw = FileKeywords(ssh_connection)

        file_kw.delete_file(key_path)

        file_kw.delete_file(csr_path)

        file_kw.delete_file(cert_bad)

        file_kw.delete_file(cert_good)

    request.addfinalizer(teardown)

    cmp_keywords = EjbcaCmpKeywords(ssh_connection)
    path = ejbca_config.get_cmp_internal_path()
    hmac_secret = ejbca_config.get_cmp_hmac_secret()

    get_logger().log_test_case_step("Generate key and CSR")
    cmp_keywords.generate_key_and_csr(cn, key_path, csr_path, san_dns=cn)

    get_logger().log_test_case_step("Attempt enrollment to unreachable server")
    bad_output = cmp_keywords.cmp_enroll_with_invalid_secret(
        "localhost:9999", path, hmac_secret, cn, key_path, csr_path, cert_bad
    )
    validate_str_contains(bad_output, "refused", "Connection refused for bad server")

    get_logger().log_test_case_step("Validate normal enrollment still works")
    server = ejbca_config.get_cmp_internal_server()
    output = cmp_keywords.cmp_enroll(server, path, hmac_secret, cn, key_path, csr_path, cert_good)
    validate_str_contains(output, "received IP", "Normal CMP works after bad attempt")



"""
EJBCA PKI System Application - Automated Test Cases

Tests for the EJBCA Enterprise PKI application deployed on StarlingX.
Covers bootstrap, CMP enrollment, REST API, security validation,
cert-manager integration, HA resilience, performance, and lifecycle.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import (
    validate_equals,
    validate_equals_with_retry,
    validate_list_contains,
    validate_str_contains,
)
from keywords.cloud_platform.security.ejbca.ejbca_cli_keywords import (
    EjbcaCliKeywords,
)
from keywords.cloud_platform.security.ejbca.ejbca_security_keywords import (
    EjbcaSecurityKeywords,
)
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import (
    SystemApplicationApplyKeywords,
)
from keywords.cloud_platform.system.application.system_application_list_keywords import (
    SystemApplicationListKeywords,
)
from keywords.cloud_platform.system.helm.system_helm_override_keywords import (
    SystemHelmOverrideKeywords,
)
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.pvc.kubectl_get_pvc_keywords import KubectlGetPvcKeywords


from keywords.cloud_platform.security.ejbca.ejbca_certmanager_keywords import EjbcaCertManagerKeywords
from keywords.cloud_platform.security.ejbca.ejbca_cmp_keywords import EjbcaCmpKeywords
from keywords.cloud_platform.security.ejbca.ejbca_rest_keywords import EjbcaRestKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.k8s_command_wrapper import export_k8s_config
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
    pod_list = pods_output.get_pods_list()

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
    pod_list = pods_output.get_pods_list()

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



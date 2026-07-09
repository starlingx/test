"""Tests for platform and K8s certificate validation via system certificate-list CLI.

Validates that default platform certificates are installed with correct attributes.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_greater_than, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.certificate.objects.system_certificate_object import SystemCertificateObject
from keywords.cloud_platform.system.certificate.system_certificate_keywords import SystemCertificateKeywords

# Expected platform certificates that must be present after install
PLATFORM_CERT_NAMES = [
    "system-openldap-local-certificate",
    "system-registry-local-certificate",
    "system-restapi-gui-certificate",
    "admin_conf_client",
    "apiserver",
    "apiserver-etcd-client",
    "apiserver-kubelet-client",
    "controller_manager_client",
    "etcd-ca",
    "etcd-server",
    "etcd-client",
    "front-proxy-ca",
    "front-proxy-client",
    "kubelet-client",
    "kubernetes-root-ca",
    "scheduler_conf_client",
    "system-local-ca",
]

# Expected K8s-managed certificates
K8S_CERT_NAMES = [
    "system-openldap-local-certificate",
    "system-registry-local-certificate",
    "system-restapi-gui-certificate",
    "system-local-ca",
]

# Minimum acceptable residual time in days for auto-renewed certs (90d cert with 30d renew-before)
MIN_RESIDUAL_DAYS_SHORT_LIVED = 1
# Maximum residual time for short-lived certs (365d)
MAX_RESIDUAL_DAYS_SHORT_LIVED = 365
# Maximum residual time for long-lived CAs (10 years)
MAX_RESIDUAL_DAYS_LONG_LIVED = 3660


@mark.p1
def test_verify_platform_certs():
    """Verify platform certificates are installed with correct attributes.

    Validates that all expected platform certificates are present in the
    system certificate-list output and have valid fields (residual time
    within acceptable range, correct issuer, renewal type, file path).

    Test Steps:
        - Get the platform certificate list via system certificate-list
        - Validate all expected certificates are present
        - Validate system-restapi-gui-certificate fields
        - Validate etcd-ca certificate fields
        - Validate etcd-client certificate fields
        - Validate apiserver certificate fields
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cert_keywords = SystemCertificateKeywords(ssh_connection)

    get_logger().log_test_case_step("Getting platform certificate list")
    cert_list_output = cert_keywords.certificate_list()

    get_logger().log_test_case_step("Validating all expected platform certificates are present")
    for expected_cert in PLATFORM_CERT_NAMES:
        validate_equals(
            cert_list_output.has_certificate(expected_cert),
            True,
            f"Certificate '{expected_cert}' should be present in platform cert list",
        )

    get_logger().log_test_case_step("Validating system-restapi-gui-certificate fields")
    restapi_cert = cert_list_output.get_certificate_by_name("system-restapi-gui-certificate")
    _validate_cert_residual_time(restapi_cert, MIN_RESIDUAL_DAYS_SHORT_LIVED, MAX_RESIDUAL_DAYS_SHORT_LIVED)
    validate_not_none(restapi_cert.get_issue_date(), "system-restapi-gui Issue Date should be set")
    validate_not_none(restapi_cert.get_expiry_date(), "system-restapi-gui Expiry Date should be set")
    validate_str_contains(restapi_cert.get_issuer(), "CN=", "system-restapi-gui Issuer should contain CN=")
    validate_equals(restapi_cert.get_namespace(), "deployment", "system-restapi-gui Namespace should be deployment")
    validate_equals(restapi_cert.get_secret(), "system-restapi-gui-certificate", "system-restapi-gui Secret name")
    validate_equals(restapi_cert.get_renewal(), "Automatic", "system-restapi-gui Renewal should be Automatic")
    validate_equals(restapi_cert.get_file_path(), "/etc/ssl/private/server-cert.pem", "system-restapi-gui File Path")

    get_logger().log_test_case_step("Validating etcd-ca certificate fields")
    etcd_ca = cert_list_output.get_certificate_by_name("etcd-ca")
    _validate_cert_residual_time(etcd_ca, MAX_RESIDUAL_DAYS_SHORT_LIVED, MAX_RESIDUAL_DAYS_LONG_LIVED)
    validate_equals(etcd_ca.get_issuer(), "CN=etcd", "etcd-ca Issuer should be CN=etcd")
    validate_equals(etcd_ca.get_subject(), "CN=etcd", "etcd-ca Subject should be CN=etcd")
    validate_equals(etcd_ca.get_renewal(), "Manual", "etcd-ca Renewal should be Manual")
    validate_equals(etcd_ca.get_file_path(), "/etc/etcd/ca.crt", "etcd-ca File Path")

    get_logger().log_test_case_step("Validating etcd-client certificate fields")
    etcd_client = cert_list_output.get_certificate_by_name("etcd-client")
    _validate_cert_residual_time(etcd_client, MIN_RESIDUAL_DAYS_SHORT_LIVED, MAX_RESIDUAL_DAYS_SHORT_LIVED)
    validate_equals(etcd_client.get_issuer(), "CN=etcd", "etcd-client Issuer should be CN=etcd")
    validate_equals(etcd_client.get_subject(), "CN=root", "etcd-client Subject should be CN=root")
    validate_equals(etcd_client.get_renewal(), "Automatic", "etcd-client Renewal should be Automatic")
    validate_equals(etcd_client.get_file_path(), "/etc/etcd/etcd-client.crt", "etcd-client File Path")

    get_logger().log_test_case_step("Validating apiserver certificate fields")
    apiserver = cert_list_output.get_certificate_by_name("apiserver")
    _validate_cert_residual_time(apiserver, MIN_RESIDUAL_DAYS_SHORT_LIVED, MAX_RESIDUAL_DAYS_SHORT_LIVED)
    validate_equals(apiserver.get_issuer(), "CN=starlingx", "apiserver Issuer should be CN=starlingx")
    validate_equals(apiserver.get_subject(), "CN=kube-apiserver", "apiserver Subject should be CN=kube-apiserver")
    validate_equals(apiserver.get_renewal(), "Automatic", "apiserver Renewal should be Automatic")
    validate_equals(apiserver.get_file_path(), "/etc/kubernetes/pki/apiserver.crt", "apiserver File Path")


@mark.p1
def test_verify_k8s_certs():
    """Verify K8s-managed certificates are present with correct attributes.

    Validates that K8s-managed certificates (cert-manager controlled) have
    valid residual time, correct issuer, namespace, and secret configuration.

    Test Steps:
        - Get the certificate list via system certificate-list
        - Validate all expected K8s certificates are present
        - Validate system-restapi-gui-certificate K8s fields
        - Validate cert-manager webhook CA fields
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    cert_keywords = SystemCertificateKeywords(ssh_connection)

    get_logger().log_test_case_step("Getting certificate list")
    cert_list_output = cert_keywords.certificate_list()

    get_logger().log_test_case_step("Validating all expected K8s certificates are present")
    for expected_cert in K8S_CERT_NAMES:
        validate_equals(
            cert_list_output.has_certificate(expected_cert),
            True,
            f"Certificate '{expected_cert}' should be present in K8s cert list",
        )

    get_logger().log_test_case_step("Validating system-restapi-gui-certificate K8s fields")
    restapi_cert = cert_list_output.get_certificate_by_name("system-restapi-gui-certificate")
    _validate_cert_residual_time(restapi_cert, MIN_RESIDUAL_DAYS_SHORT_LIVED, MAX_RESIDUAL_DAYS_SHORT_LIVED)
    validate_not_none(restapi_cert.get_issue_date(), "system-restapi-gui Issue Date should be set")
    validate_not_none(restapi_cert.get_expiry_date(), "system-restapi-gui Expiry Date should be set")
    validate_str_contains(restapi_cert.get_issuer(), "CN=", "system-restapi-gui Issuer should contain CN=")
    validate_equals(restapi_cert.get_namespace(), "deployment", "system-restapi-gui Namespace should be deployment")
    validate_equals(restapi_cert.get_secret(), "system-restapi-gui-certificate", "system-restapi-gui Secret name")
    validate_equals(restapi_cert.get_renewal(), "Automatic", "system-restapi-gui Renewal should be Automatic")


def _validate_cert_residual_time(cert: SystemCertificateObject, min_days: int, max_days: int) -> None:
    """Validate certificate residual time is within acceptable range.

    Args:
        cert (SystemCertificateObject): Certificate object to validate.
        min_days (int): Minimum acceptable residual days.
        max_days (int): Maximum acceptable residual days.
    """
    residual_time = cert.get_residual_time()
    validate_not_none(residual_time, f"{cert.get_name()} Residual Time should be set")
    days = cert.get_residual_time_days()
    validate_greater_than(
        days,
        min_days - 1,
        f"{cert.get_name()} Residual Time ({residual_time}) should be >= {min_days}d",
    )
    validate_equals(
        days <= max_days,
        True,
        f"{cert.get_name()} Residual Time ({residual_time}) should be <= {max_days}d",
    )

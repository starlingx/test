"""Coverage for the kube-cert-rotation.sh K8s certificate renewal script.

Improves test coverage for /usr/bin/kube-cert-rotation.sh, the test-escape
follow (K8s certificates were not renewed on a customer system).

Two scenarios are covered, per the guidance:
    - The script renews a K8s leaf certificate (apiserver) that is near expiry.
    - The script does NOT renew certificates that are still valid.

The near-expiry apiserver certificate is forced using the procedure validated in
a new apiserver leaf certificate is generated and signed by the real
K8s Root CA (/etc/kubernetes/pki/ca.crt + ca.key) WITH the required X.509 v3
extensions (subjectAltName copied from the live cert, keyUsage,
extendedKeyUsage=serverAuth, basicConstraints=CA:FALSE). Signing without
extendedKeyUsage reproduces the kubeadm failure
'must specify at least one ExtKeyUsage', so the extensions are mandatory.

WARNING: These tests replace the live apiserver certificate and restart the
apiserver. A backup/restore finalizer restores the original apiserver.crt/.key and
restarts the apiserver on teardown, even on failure.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.security.kube_cert_rotation_keywords import KubeCertRotationKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.certificate.system_certificate_keywords import SystemCertificateKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.openssl.openssl_keywords import OpenSSLKeywords

APISERVER_CERT = "/etc/kubernetes/pki/apiserver.crt"
APISERVER_KEY = "/etc/kubernetes/pki/apiserver.key"
WORKING_DIR = "/home/sysadmin/kube_cert_rotation_test"


def _get_apiserver_residual_days(ssh_connection: SSHConnection) -> int:
    """Return the apiserver certificate residual time in days via system certificate-list.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.

    Returns:
        int: Residual time (days) of the 'apiserver' certificate.
    """
    cert_list = SystemCertificateKeywords(ssh_connection).certificate_list()
    apiserver_cert = cert_list.get_certificate_by_name("apiserver")
    return apiserver_cert.get_residual_time_days()


def _install_short_lived_apiserver_cert(ssh_connection: SSHConnection, days: int) -> None:
    """Generate and install a short-lived apiserver certificate signed by the K8s Root CA.

    Follows the create a leaf key + CSR, build an
    extensions file (SAN from the live cert, keyUsage, extendedKeyUsage=serverAuth,
    basicConstraints=CA:FALSE), sign with the K8s Root CA, install as the apiserver
    cert/key, and restart the apiserver so it serves the short-lived certificate.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
        days (int): Validity, in days, for the generated apiserver certificate.
    """
    file_keywords = FileKeywords(ssh_connection)
    openssl = OpenSSLKeywords(ssh_connection)
    rotation_keywords = KubeCertRotationKeywords(ssh_connection)

    file_keywords.create_directory(WORKING_DIR)
    leaf_key = f"{WORKING_DIR}/leaf.key"
    leaf_csr = f"{WORKING_DIR}/leaf.csr"
    leaf_crt = f"{WORKING_DIR}/leaf.crt"
    ext_file = f"{WORKING_DIR}/leaf_ext.cnf"

    sans = rotation_keywords.get_apiserver_sans()
    ext_contents = "[v3_ca]\n" f"subjectAltName = {sans}\n" "keyUsage = critical, digitalSignature, keyEncipherment\n" "extendedKeyUsage = TLS Web Server Authentication\n" "basicConstraints = critical, CA:FALSE\n"
    file_keywords.create_file_with_heredoc(ext_file, ext_contents)

    get_logger().log_test_case_step(f"Generate an apiserver leaf cert valid for {days} days, signed by the K8s Root CA")
    openssl.generate_rsa_key(leaf_key, bits=2048)
    openssl.create_certificate_signing_request(leaf_key, leaf_csr, subj="/CN=kube-apiserver")

    # The K8s Root CA cert/key under /etc/kubernetes/pki are root-only, so the
    # (non-sudo) openssl signing cannot read them. Copy readable duplicates into
    # the working dir (removed on teardown) and sign against those, matching the
    # CGTS-72399-validated procedure.
    ca_cert_copy = f"{WORKING_DIR}/ca.crt"
    ca_key_copy = f"{WORKING_DIR}/ca.key"
    rotation_keywords.copy_k8s_ca_readable(ca_cert_copy, ca_key_copy)

    openssl.sign_certificate_with_extensions(
        {"csr": leaf_csr, "ca_cert": ca_cert_copy, "ca_key": ca_key_copy, "cert": leaf_crt},
        ext_file,
        days=days,
        extensions="v3_ca",
    )

    get_logger().log_test_case_step("Install the short-lived apiserver certificate and restart the apiserver")
    file_keywords.copy_file(leaf_crt, APISERVER_CERT, sudo=True)
    file_keywords.copy_file(leaf_key, APISERVER_KEY, sudo=True)
    rotation_keywords.restart_apiserver()


def _backup_apiserver_cert(ssh_connection: SSHConnection) -> None:
    """Back up the live apiserver certificate and key into the working directory.

    Args:
        ssh_connection (SSHConnection): Active controller SSH connection.
    """
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.create_directory(WORKING_DIR)
    get_logger().log_test_case_step("Back up the original apiserver certificate and key")
    file_keywords.copy_file(APISERVER_CERT, f"{WORKING_DIR}/apiserver.crt.bak", sudo=True)
    file_keywords.copy_file(APISERVER_KEY, f"{WORKING_DIR}/apiserver.key.bak", sudo=True)


def _restore_apiserver_cert() -> None:
    """Restore the original apiserver certificate/key and restart the apiserver.

    Opens a fresh SSH connection so restoration is robust even if the connection
    used during the test was affected by the apiserver restarts.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_teardown_step("Restore the original apiserver certificate and key, restart apiserver")
    file_keywords = FileKeywords(ssh_connection)
    file_keywords.copy_file(f"{WORKING_DIR}/apiserver.crt.bak", APISERVER_CERT, sudo=True)
    file_keywords.copy_file(f"{WORKING_DIR}/apiserver.key.bak", APISERVER_KEY, sudo=True)
    KubeCertRotationKeywords(ssh_connection).restart_apiserver()
    file_keywords.delete_directory(WORKING_DIR)


@mark.p2
def test_kube_cert_rotation_renews_expiring_apiserver_cert(request: FixtureRequest):
    """Verify kube-cert-rotation.sh renews a near-expiry apiserver certificate.

    Forces a short-lived (5-day) apiserver certificate signed by the K8s Root CA,
    confirms its residual time is low, runs kube-cert-rotation.sh, then confirms
    the apiserver certificate has been renewed (residual time back to roughly a
    year).

    Teardown:
        - Restore the original apiserver certificate/key and restart the apiserver
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()
    get_logger().log_test_case_step(f"Testing kube-cert-rotation.sh on controller with OAM {lab_oam_ip}")
    _backup_apiserver_cert(ssh_connection)
    request.addfinalizer(_restore_apiserver_cert)

    get_logger().log_test_case_step("Install a 5-day apiserver certificate to force near-expiry")
    _install_short_lived_apiserver_cert(ssh_connection, days=5)

    get_logger().log_test_case_step("Confirm the apiserver certificate is near expiry")
    residual_before = _get_apiserver_residual_days(ssh_connection)
    get_logger().log_info(f"apiserver residual days before rotation: {residual_before}")
    validate_equals(residual_before <= 7, True, "apiserver certificate should be near expiry (<= 7 days) before rotation")

    output = KubeCertRotationKeywords(ssh_connection).run_rotation_script()
    validate_equals("failed to renew" in output.lower(), False, "kube-cert-rotation.sh should not report a renewal failure")

    get_logger().log_test_case_step("Wait for the apiserver to recover (the script restarts it) and confirm renewal")
    # kube-cert-rotation.sh restarts the apiserver itself, so only wait for the API
    # to come back - do NOT trigger another restart (matches CGTS-72399 steps 6-7).
    KubeCertRotationKeywords(ssh_connection).wait_for_api_available()

    def apiserver_renewed() -> bool:
        """Return True once the apiserver certificate residual time exceeds 30 days."""
        return _get_apiserver_residual_days(ssh_connection) > 30

    validate_equals_with_retry(
        function_to_execute=apiserver_renewed,
        expected_value=True,
        validation_description="Waiting for the apiserver certificate to be renewed (residual > 30 days)",
        timeout=300,
        polling_sleep_time=15,
    )

    residual_after = _get_apiserver_residual_days(ssh_connection)
    get_logger().log_info(f"apiserver residual days after rotation: {residual_after}")
    validate_equals(residual_after > 30, True, "apiserver certificate should be renewed (residual > 30 days) after kube-cert-rotation.sh")


@mark.p2
def test_kube_cert_rotation_skips_valid_certs(request: FixtureRequest):
    """Verify kube-cert-rotation.sh does NOT renew certificates that are still valid.

    With the apiserver certificate still valid (long residual time), runs
    kube-cert-rotation.sh and confirms the certificate's expiry date is unchanged,
    i.e. the script correctly skips renewal when nothing is near expiry.

    Teardown:
        - Restore the original apiserver certificate/key and restart the apiserver
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_oam_ip = ConfigurationManager.get_lab_config().get_floating_ip()
    get_logger().log_test_case_step(f"Testing kube-cert-rotation.sh (no-renewal case) on controller with OAM {lab_oam_ip}")
    _backup_apiserver_cert(ssh_connection)
    request.addfinalizer(_restore_apiserver_cert)

    get_logger().log_test_case_step("Capture the apiserver certificate expiry date before running the script")
    cert_before = SystemCertificateKeywords(ssh_connection).certificate_list().get_certificate_by_name("apiserver")
    expiry_before = cert_before.get_expiry_date()
    residual_before = cert_before.get_residual_time_days()
    get_logger().log_info(f"apiserver expiry before: {expiry_before} (residual {residual_before} days)")
    validate_equals(residual_before > 30, True, "Precondition: apiserver certificate should be valid (residual > 30 days)")

    KubeCertRotationKeywords(ssh_connection).run_rotation_script()

    get_logger().log_test_case_step("Confirm the valid apiserver certificate was NOT renewed (expiry unchanged)")
    cert_after = SystemCertificateKeywords(ssh_connection).certificate_list().get_certificate_by_name("apiserver")
    expiry_after = cert_after.get_expiry_date()
    get_logger().log_info(f"apiserver expiry after: {expiry_after}")
    validate_equals(expiry_after, expiry_before, "A valid apiserver certificate must NOT be renewed by kube-cert-rotation.sh (expiry unchanged)")

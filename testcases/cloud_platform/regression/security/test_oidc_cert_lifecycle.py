"""OIDC certificate-lifecycle and pod-recovery tests for oidc-auth-apps.

Covers the dex/oidc-client pod recovery and certificate-change behaviour:
    - oidc pods are recreated automatically after deletion, and access still works
    - a user retains OIDC access while the app is applied with its certificate
    - when the oidc-auth-apps certificate is renewed, the secret-observer cronjob
      recycles the dex/oidc-client pods with the new cert and access still works

It also covers the Distributed Cloud variants of the certificate lifecycle on
the System Controller and a subcloud, plus subcloud id-token expiry.

Lab preconditions, which these tests do not create:
    - oidc-auth-apps installed on the system.
    - Local LDAP available for the dex connector.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry, validate_not_equals
from keywords.cloud_platform.security.oidc.oidc_auth_keywords import OidcAuthKeywords
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import OIDC_NAMESPACE, OidcSetupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.clusterrolebinding.kubectl_create_clusterrolebinding_keywords import KubectlCreateClusterRoleBindingKeywords
from keywords.k8s.jobs.kubectl_create_jobs_keywords import KubectlCreateJobsKeywords
from keywords.k8s.jobs.kubectl_delete_jobs_keywords import KubectlDeleteJobsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.k8s.secret.kubectl_delete_secret_keywords import KubectlDeleteSecretsKeywords

OIDC_CERT = "oidc-auth-apps-certificate"
SECRET_OBSERVER_CRONJOB = "secret-observer-cron-job"
CERT_RENEW_JOB = "secret-observer-cert-renew-test"
TEST_GROUP = "pvtestgroup"
CERT_RENEW_TIMEOUT = 600
POD_READY_TIMEOUT = 300
TOKEN_EXPIRY_SECONDS = 60
TOKEN_EXPIRY_TIMEOUT = 180


@mark.p2
def test_oidc_delete_pods(request: FixtureRequest):
    """Verify oidc pods are recreated after deletion and user access still works.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user
        - Delete the dex and oidc-client pods
        - Verify the pods are recreated and reach Running
        - Verify the LDAP user still has OIDC access to the Kubernetes API
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_podrecovery_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC environment, role-bindings and LDAP user")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Delete the dex and oidc-client pods")
    original_pods = oidc_setup.get_oidc_pod_names()
    oidc_setup.delete_oidc_pods_and_wait_ready(original_pods, timeout=POD_READY_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user still has OIDC access")
    oidc_setup.verify_user_access(oam_ip, username, password)


@mark.p2
def test_oidc_app_with_oidc_cert(request: FixtureRequest):
    """Verify a user retains OIDC access while oidc-auth-apps is applied with its cert.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user
        - Verify the oidc-auth-apps certificate is ready
        - Verify the LDAP user has OIDC access to the Kubernetes API
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_cert_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC environment, role-bindings and LDAP user")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Verify the oidc-auth-apps certificate is ready")
    cert_keywords.wait_for_certs_status(OIDC_CERT, is_ready=True, namespace=OIDC_NAMESPACE, timeout=CERT_RENEW_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user has OIDC access")
    oidc_setup.verify_user_access(oam_ip, username, password)


@mark.p2
def test_oidc_pods_restarted_with_oidc_cert_changes(request: FixtureRequest):
    """Verify cert renewal recycles oidc pods via the cronjob and access still works.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user
        - Record the current oidc-auth-apps certificate expiry
        - Wait for the certificate to be renewed (expiry advances)
        - Trigger the secret-observer cronjob to recycle the pods with the new cert
        - Verify the old dex and oidc-client pods are replaced and reach Running
        - Verify the LDAP user still has OIDC access to the Kubernetes API
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_certchange_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    create_jobs_keywords = KubectlCreateJobsKeywords(ssh_connection)
    delete_jobs_keywords = KubectlDeleteJobsKeywords(ssh_connection)
    delete_secret_keywords = KubectlDeleteSecretsKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: delete_jobs_keywords.delete_job(CERT_RENEW_JOB, OIDC_NAMESPACE))
    request.addfinalizer(lambda: crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC environment, role-bindings and LDAP user")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Record the current certificate expiry and oidc pods")
    initial_not_after = cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE)
    original_pods = oidc_setup.get_oidc_pod_names()

    get_logger().log_test_case_step("Force certificate renewal by deleting the certificate secret")
    delete_secret_keywords.delete_secret(OIDC_CERT, OIDC_NAMESPACE)
    validate_equals_with_retry(
        lambda: cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE) not in ("", initial_not_after),
        True,
        "oidc-auth-apps certificate should be re-issued with a new expiry",
        timeout=CERT_RENEW_TIMEOUT,
        polling_sleep_time=10,
    )
    renewed_not_after = cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE)
    validate_not_equals(renewed_not_after, initial_not_after, "Certificate expiry must differ after re-issue")

    get_logger().log_test_case_step("Trigger the secret-observer cronjob to recycle the oidc pods")
    delete_jobs_keywords.delete_job(CERT_RENEW_JOB, OIDC_NAMESPACE)
    create_jobs_keywords.create_job_from_cronjob(CERT_RENEW_JOB, SECRET_OBSERVER_CRONJOB, namespace=OIDC_NAMESPACE)

    get_logger().log_test_case_step("Verify old oidc pods are replaced and reach Running")
    oidc_setup.wait_for_oidc_pods_recycled(original_pods, timeout=POD_READY_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user still has OIDC access")
    oidc_setup.verify_user_access(oam_ip, username, password)


@mark.p2
@mark.lab_has_subcloud
def test_oidc_app_with_oidc_cert_central(request: FixtureRequest):
    """Verify a user retains OIDC access on the System Controller with the app cert.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user on the SC
        - Verify the oidc-auth-apps certificate is ready on the SC
        - Verify the LDAP user has OIDC access to the System Controller API
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_cert_central_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Verify the oidc-auth-apps certificate is ready on the SC")
    cert_keywords.wait_for_certs_status(OIDC_CERT, is_ready=True, namespace=OIDC_NAMESPACE, timeout=CERT_RENEW_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user has OIDC access on the System Controller")
    oidc_setup.verify_user_access(oam_ip, username, password)


@mark.p2
@mark.lab_has_subcloud
def test_oidc_pods_restarted_with_oidc_cert_changes_central(request: FixtureRequest):
    """Verify cert renewal recycles the SC oidc pods and access still works.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user on the SC
        - Force certificate renewal by deleting the certificate secret
        - Trigger the secret-observer cronjob to recycle the pods with the new cert
        - Verify the old oidc pods are replaced and reach Running
        - Verify the LDAP user still has OIDC access on the System Controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    oam_ip = lab_config.get_floating_ip()
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_certchg_central_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    create_jobs_keywords = KubectlCreateJobsKeywords(ssh_connection)
    delete_jobs_keywords = KubectlDeleteJobsKeywords(ssh_connection)
    delete_secret_keywords = KubectlDeleteSecretsKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: delete_jobs_keywords.delete_job(CERT_RENEW_JOB, OIDC_NAMESPACE))
    request.addfinalizer(lambda: crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Record the current certificate expiry and oidc pods")
    initial_not_after = cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE)
    original_pods = oidc_setup.get_oidc_pod_names()

    get_logger().log_test_case_step("Force certificate renewal by deleting the certificate secret")
    delete_secret_keywords.delete_secret(OIDC_CERT, OIDC_NAMESPACE)
    validate_equals_with_retry(
        lambda: cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE) not in ("", initial_not_after),
        True,
        "oidc-auth-apps certificate should be re-issued with a new expiry",
        timeout=CERT_RENEW_TIMEOUT,
        polling_sleep_time=10,
    )
    renewed_not_after = cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE)
    validate_not_equals(renewed_not_after, initial_not_after, "Certificate expiry must differ after re-issue")

    get_logger().log_test_case_step("Trigger the secret-observer cronjob to recycle the oidc pods")
    delete_jobs_keywords.delete_job(CERT_RENEW_JOB, OIDC_NAMESPACE)
    create_jobs_keywords.create_job_from_cronjob(CERT_RENEW_JOB, SECRET_OBSERVER_CRONJOB, namespace=OIDC_NAMESPACE)

    get_logger().log_test_case_step("Verify old oidc pods are replaced and reach Running")
    oidc_setup.wait_for_oidc_pods_recycled(original_pods, timeout=POD_READY_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user still has OIDC access on the System Controller")
    oidc_setup.verify_user_access(oam_ip, username, password)


@mark.p2
@mark.lab_has_subcloud
def test_oidc_app_with_oidc_cert_subcloud(request: FixtureRequest):
    """Verify a subcloud user retains OIDC access via the System Controller's dex.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user on the SC
        - Create the CRB on the subcloud for the user
        - Verify the oidc-auth-apps certificate is ready on the SC
        - Verify the LDAP user has OIDC access to the subcloud API
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_oam_ip = lab_config.get_subcloud(subcloud_name).get_floating_ip()
    sc_oam_ip = lab_config.get_floating_ip()
    sc_bracketed = f"[{sc_oam_ip}]" if ":" in sc_oam_ip else sc_oam_ip
    sc_oidc_issuer = f"https://{sc_bracketed}:30556/dex"
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_cert_subcloud_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    sc_crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    subcloud_crb_keywords = KubectlCreateClusterRoleBindingKeywords(subcloud_ssh)
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: sc_crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: subcloud_crb_keywords.cleanup_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)

    get_logger().log_test_case_step("Create the CRB on the subcloud for the test group")
    subcloud_crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Point the subcloud kube-apiserver at the System Controller dex")
    oidc_setup.configure_subcloud_oidc_issuer(subcloud_ssh, sc_oidc_issuer)

    get_logger().log_test_case_step("Verify the oidc-auth-apps certificate is ready on the SC")
    cert_keywords.wait_for_certs_status(OIDC_CERT, is_ready=True, namespace=OIDC_NAMESPACE, timeout=CERT_RENEW_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user has OIDC access on the subcloud")
    oidc_setup.verify_user_access(subcloud_oam_ip, username, password, oidc_client_ip=sc_oam_ip)


@mark.p2
@mark.lab_has_subcloud
def test_oidc_pods_restarted_with_oidc_cert_changes_subcloud(request: FixtureRequest):
    """Verify SC cert renewal recycles oidc pods and a subcloud user keeps access.

    Test Steps:
        - Set up OIDC with local LDAP, role-bindings and an LDAP test user on the SC
        - Create the CRB on the subcloud for the user
        - Force certificate renewal by deleting the certificate secret on the SC
        - Trigger the secret-observer cronjob to recycle the SC oidc pods
        - Verify the old oidc pods are replaced and reach Running
        - Verify the LDAP user still has OIDC access on the subcloud
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_oam_ip = lab_config.get_subcloud(subcloud_name).get_floating_ip()
    sc_oam_ip = lab_config.get_floating_ip()
    sc_bracketed = f"[{sc_oam_ip}]" if ":" in sc_oam_ip else sc_oam_ip
    sc_oidc_issuer = f"https://{sc_bracketed}:30556/dex"
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_certchg_subcloud_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    sc_crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    subcloud_crb_keywords = KubectlCreateClusterRoleBindingKeywords(subcloud_ssh)
    cert_keywords = KubectlGetCertStatusKeywords(ssh_connection)
    create_jobs_keywords = KubectlCreateJobsKeywords(ssh_connection)
    delete_jobs_keywords = KubectlDeleteJobsKeywords(ssh_connection)
    delete_secret_keywords = KubectlDeleteSecretsKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: delete_jobs_keywords.delete_job(CERT_RENEW_JOB, OIDC_NAMESPACE))
    request.addfinalizer(lambda: sc_crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: subcloud_crb_keywords.cleanup_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller")
    oidc_setup.setup_oidc_environment()
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    subcloud_crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Point the subcloud kube-apiserver at the System Controller dex")
    oidc_setup.configure_subcloud_oidc_issuer(subcloud_ssh, sc_oidc_issuer)

    get_logger().log_test_case_step("Record the current certificate expiry and oidc pods")
    initial_not_after = cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE)
    original_pods = oidc_setup.get_oidc_pod_names()

    get_logger().log_test_case_step("Force certificate renewal by deleting the certificate secret")
    delete_secret_keywords.delete_secret(OIDC_CERT, OIDC_NAMESPACE)
    validate_equals_with_retry(
        lambda: cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE) not in ("", initial_not_after),
        True,
        "oidc-auth-apps certificate should be re-issued with a new expiry",
        timeout=CERT_RENEW_TIMEOUT,
        polling_sleep_time=10,
    )
    renewed_not_after = cert_keywords.get_certificate_not_after(OIDC_CERT, namespace=OIDC_NAMESPACE)
    validate_not_equals(renewed_not_after, initial_not_after, "Certificate expiry must differ after re-issue")

    get_logger().log_test_case_step("Trigger the secret-observer cronjob to recycle the oidc pods")
    delete_jobs_keywords.delete_job(CERT_RENEW_JOB, OIDC_NAMESPACE)
    create_jobs_keywords.create_job_from_cronjob(CERT_RENEW_JOB, SECRET_OBSERVER_CRONJOB, namespace=OIDC_NAMESPACE)

    get_logger().log_test_case_step("Verify old oidc pods are replaced and reach Running")
    oidc_setup.wait_for_oidc_pods_recycled(original_pods, timeout=POD_READY_TIMEOUT)

    get_logger().log_test_case_step("Verify the LDAP user still has OIDC access on the subcloud")
    oidc_setup.verify_user_access(subcloud_oam_ip, username, password, oidc_client_ip=sc_oam_ip)


@mark.p2
@mark.lab_has_subcloud
def test_oidc_id_token_expiry_subcloud(request: FixtureRequest):
    """Verify a subcloud user loses OIDC access once the id token expires.

    Test Steps:
        - Set up OIDC on the SC with a short id token expiry
        - Create the CRB on the subcloud for the user
        - Verify the LDAP user initially has OIDC access on the subcloud
        - Wait for the id token to expire
        - Verify the cached token no longer grants access on the subcloud
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    lab_config = ConfigurationManager.get_lab_config()
    subcloud_name = lab_config.get_subcloud_names()[0]
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
    subcloud_oam_ip = lab_config.get_subcloud(subcloud_name).get_floating_ip()
    sc_oam_ip = lab_config.get_floating_ip()
    sc_bracketed = f"[{sc_oam_ip}]" if ":" in sc_oam_ip else sc_oam_ip
    sc_oidc_issuer = f"https://{sc_bracketed}:30556/dex"
    password = lab_config.get_admin_credentials().get_password()
    username = "oidc_expiry_subcloud_user01"

    oidc_setup = OidcSetupKeywords(ssh_connection)
    sc_crb_keywords = KubectlCreateClusterRoleBindingKeywords(ssh_connection)
    subcloud_crb_keywords = KubectlCreateClusterRoleBindingKeywords(subcloud_ssh)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)
    request.addfinalizer(lambda: sc_crb_keywords.delete_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: subcloud_crb_keywords.cleanup_clusterrolebinding(TEST_GROUP))
    request.addfinalizer(lambda: oidc_setup.cleanup_ldap_user(username, password, TEST_GROUP))

    get_logger().log_setup_step("Set up OIDC on the System Controller with a short id token expiry")
    oidc_setup.setup_oidc_environment(id_token_expiry=f"{TOKEN_EXPIRY_SECONDS}s")
    request.addfinalizer(oidc_setup.setup_role_bindings(TEST_GROUP, "admin"))
    oidc_setup.setup_ldap_user(username, password, TEST_GROUP)
    subcloud_crb_keywords.create_clusterrolebinding_for_user(TEST_GROUP, "cluster-admin", f"%{TEST_GROUP}")

    get_logger().log_test_case_step("Point the subcloud kube-apiserver at the System Controller dex")
    oidc_setup.configure_subcloud_oidc_issuer(subcloud_ssh, sc_oidc_issuer)

    get_logger().log_test_case_step("Verify the LDAP user initially has OIDC access on the subcloud")
    ldap_ssh = OidcAuthKeywords.create_ldap_user_ssh(subcloud_oam_ip, username, password, oidc_client_ip=sc_oam_ip)
    KubectlGetPodsKeywords(ldap_ssh).get_pods()

    get_logger().log_test_case_step("Wait for the id token to expire and verify access is blocked")
    validate_equals_with_retry(
        lambda: oidc_setup.is_user_access_denied(ldap_ssh),
        True,
        "Subcloud OIDC access should be denied after the id token expires",
        timeout=TOKEN_EXPIRY_TIMEOUT,
        polling_sleep_time=15,
    )

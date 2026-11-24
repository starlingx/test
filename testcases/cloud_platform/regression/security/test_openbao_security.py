"""OpenBao application security tests.

Covers the OpenBao application (container) security scenarios that validate the
server over its Kubernetes service endpoint:
    - server TLS: trusted-CA client succeeds, no-CA client is rejected, the
      server certificate verifies against the OpenBao CA
    - RBAC: a read-only policy/role allows reads but denies writes
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.openbao.openbao_keywords import OpenBaoKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "openbao"
CHART_PATH = "/usr/local/share/applications/helm/openbao-[0-9]*"
NAMESPACE = "openbao"
TEST_NAMESPACE = "pvtest"
POLICY_NAME = "basic-secret-policy"
ROLE_NAME = "basic-secret-role"
SERVICE_ACCOUNT = "basic-secret"
POLICY_HCL = 'path "secret/data/basic-secret/*" { capabilities = ["read"] }'


def setup_openbao_environment(ssh_connection: object) -> None:
    """Upload and apply OpenBao, wait for unseal, and configure KV v2 + k8s auth.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    app_list = SystemApplicationListKeywords(ssh_connection)
    validate_equals(app_list.is_app_present("platform-integ-apps"), True, "platform-integ-apps must be present for OpenBao PVC")

    if not app_list.is_app_present(APP_NAME):
        get_logger().log_info(f"Uploading {APP_NAME} application")
        actual_chart = LsKeywords(ssh_connection).get_first_matching_file(CHART_PATH)
        upload_input = SystemApplicationUploadInput()
        upload_input.set_tar_file_path(actual_chart)
        upload_input.set_app_name(APP_NAME)
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(upload_input)

    app_apply = SystemApplicationApplyKeywords(ssh_connection)
    if not app_apply.is_already_applied(APP_NAME):
        get_logger().log_info(f"Applying {APP_NAME} application")
        app_apply.system_application_apply(APP_NAME)

    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)

    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    unsealed = openbao.wait_for_unseal(timeout=300)
    validate_equals(unsealed, True, "OpenBao should be unsealed after apply")

    openbao.extract_ca_cert()

    root_token = openbao.get_root_token()
    openbao.enable_kv_v2(root_token)
    openbao.enable_kubernetes_auth(root_token)
    openbao.write_policy(POLICY_NAME, POLICY_HCL, root_token)
    openbao.write_kubernetes_role(ROLE_NAME, SERVICE_ACCOUNT, TEST_NAMESPACE, POLICY_NAME, root_token)


def cleanup_openbao_environment(ssh_connection: object) -> None:
    """Clean up OpenBao security test resources and remove the application.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    get_logger().log_teardown_step("Cleaning up OpenBao security test resources")

    KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(TEST_NAMESPACE)

    app_list = SystemApplicationListKeywords(ssh_connection)
    if app_list.is_app_present(APP_NAME):
        app_apply = SystemApplicationApplyKeywords(ssh_connection)
        if app_apply.is_already_applied(APP_NAME):
            remove_input = SystemApplicationRemoveInput()
            remove_input.set_app_name(APP_NAME)
            SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)

        delete_input = SystemApplicationDeleteInput()
        delete_input.set_app_name(APP_NAME)
        delete_input.set_force_deletion(True)
        SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)


@mark.p1
def test_openbao_server_tls_verify(request: FixtureRequest):
    """Test that the OpenBao application server enforces TLS with a CA-issued cert.

    A client trusting the OpenBao CA can reach the server health endpoint over
    TLS, a client with no trusted CA is rejected, and the server certificate
    verifies against the OpenBao CA.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - query the health endpoint trusting the CA and confirm it is reachable
        - query the health endpoint with no trusted CA and confirm rejection
        - verify the server certificate against the OpenBao CA
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Querying the health endpoint over TLS while trusting the OpenBao CA")
    validate_equals(openbao.rest_health_trusts_ca(), True, "Health endpoint must be reachable over TLS trusting the OpenBao CA")

    get_logger().log_test_case_step("Querying the health endpoint with no trusted CA and confirming rejection")
    validate_equals(openbao.rest_health_no_ca_rejected(), True, "Health request without a trusted CA must be rejected by TLS verification")

    get_logger().log_test_case_step("Verifying the server certificate validates against the OpenBao CA")
    validate_equals(openbao.app_server_cert_verifies(), True, "Server certificate must verify against the OpenBao CA")


@mark.p1
def test_openbao_rbac_read_only_policy(request: FixtureRequest):
    """Test that the read-only RBAC policy allows reads but denies writes.

    A kubernetes-auth role bound to a read-only policy on the bound secret path
    can read the secret but is denied writes to the bound path and to an
    out-of-policy path.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - seed the bound secret and the RBAC test service account
        - log in via the kubernetes role to obtain a scoped token
        - read the bound path and confirm it is allowed
        - write the bound path and confirm it is denied
        - write an out-of-policy path and confirm it is denied
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Seeding the bound secret and the RBAC test service account")
    root_token = openbao.get_root_token()
    openbao.create_secret_rest("basic-secret/helloworld", {"username": security_config.get_openbao_test_secret_username(), "password": security_config.get_openbao_test_secret_password()}, root_token)
    openbao.ensure_rbac_test_subject(TEST_NAMESPACE, SERVICE_ACCOUNT)

    get_logger().log_test_case_step("Logging in via the kubernetes role to obtain a scoped token")
    role_token = openbao.k8s_role_login_token(ROLE_NAME, SERVICE_ACCOUNT, TEST_NAMESPACE)
    validate_not_equals(role_token, "", "Kubernetes role login must return a scoped client token")

    get_logger().log_test_case_step("Reading the bound path and confirming the read is allowed")
    validate_equals(openbao.rest_status_code("basic-secret/helloworld", role_token), "200", "Read-only role must be allowed to read the bound path")

    get_logger().log_test_case_step("Writing the bound path and confirming the write is denied")
    validate_equals(openbao.rest_write_status_code("basic-secret/helloworld", role_token), "403", "Read-only role must be denied writes to the bound path")

    get_logger().log_test_case_step("Writing an out-of-policy path and confirming the write is denied")
    validate_equals(openbao.rest_write_status_code("out-of-policy/secret", role_token), "403", "Read-only role must be denied writes to an out-of-policy path")


@mark.p2
def test_openbao_audit_device_logs_access(request: FixtureRequest):
    """Test that an enabled audit device records secret access requests.

    A file audit device is enabled, a secret is read over the REST API, and the
    in-pod audit log contains an entry for that secret path. The audit device is
    disabled again in cleanup so no persistent device is left behind.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - enable a file audit device and seed a secret
        - read the secret over REST to generate an audit event
        - confirm the audit log records the secret path
        - Teardown: disable the audit device and clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    audit_name = "file-audit"
    audit_file = "/openbao/audit/audit.log"

    def cleanup():
        get_logger().log_teardown_step("Disabling the audit device and cleaning up the OpenBao environment")
        try:
            openbao.disable_audit_device(audit_name, openbao.get_root_token())
        finally:
            cleanup_openbao_environment(ssh_connection)

    request.addfinalizer(cleanup)
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Enabling a file audit device and seeding a secret")
    root_token = openbao.get_root_token()
    openbao.enable_audit_device(audit_name, audit_file, root_token)
    validate_str_contains(openbao.list_audit_devices(root_token), audit_name, "Enabled audit device must be listed")
    openbao.create_secret_rest("basic-secret/audited", {"k": "v"}, root_token)

    get_logger().log_test_case_step("Reading the secret over REST to generate an audit event")
    validate_equals(openbao.rest_status_code("basic-secret/audited", root_token), "200", "Secret read must succeed to generate an audit event")

    get_logger().log_test_case_step("Confirming the audit log records the secret path")
    validate_str_contains(openbao.read_pod_audit_log(audit_file, "basic-secret/audited"), "basic-secret/audited", "Audit log must contain an entry for the accessed secret path")


@mark.p1
def test_openbao_auth_enforcement_rejects_bad_token(request: FixtureRequest):
    """Test that the OpenBao API rejects access without a valid token.

    A request with no token and a request with an invalid token are both denied,
    while a request with the valid root token succeeds, confirming the server
    enforces authentication on secret paths.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - seed a secret with the root token
        - request the secret with no token and confirm rejection with HTTP 403
        - request the secret with an invalid token and confirm rejection with HTTP 403
        - request the secret with the valid token and confirm success
        - Teardown: clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Seeding a secret with the root token")
    root_token = openbao.get_root_token()
    openbao.create_secret_rest("basic-secret/authcheck", {"k": "v"}, root_token)

    get_logger().log_test_case_step("Requesting the secret with no token and confirming rejection with HTTP 403")
    validate_equals(openbao.rest_status_code("basic-secret/authcheck", None), "403", "Request with no token must be rejected with permission denied")

    get_logger().log_test_case_step("Requesting the secret with an invalid token and confirming rejection with HTTP 403")
    validate_equals(openbao.rest_status_code("basic-secret/authcheck", "invalid-token-value"), "403", "Request with an invalid token must be rejected with permission denied")

    get_logger().log_test_case_step("Requesting the secret with the valid token and confirming success")
    validate_equals(openbao.rest_status_code("basic-secret/authcheck", root_token), "200", "Request with the valid root token must be granted access")


@mark.p2
def test_openbao_server_pod_auto_unseals_on_restart(request: FixtureRequest):
    """Test that a restarted OpenBao server pod auto-unseals without intervention.

    The running server pod is deleted; the replacement pod reads its unseal
    material from the cluster secret and returns to a ready, unsealed state with
    no manual unseal, and a previously stored secret is served again.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - seed a secret with the root token
        - delete the running server pod to force a restart
        - confirm the server auto-unseals back to a ready state
        - confirm the previously stored secret is served again
        - Teardown: clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Seeding a secret with the root token")
    root_token = openbao.get_root_token()
    openbao.create_secret_rest("basic-secret/restartcheck", {"k": "v"}, root_token)

    get_logger().log_test_case_step("Deleting the running server pod to force a restart")
    server_pod = openbao.get_server_pod_name()
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(server_pod, namespace=NAMESPACE)

    get_logger().log_test_case_step("Confirming the server auto-unseals back to a ready state")
    validate_equals(openbao.wait_for_unseal(), True, "Server pod must auto-unseal and become ready after restart with no manual intervention")

    get_logger().log_test_case_step("Confirming the previously stored secret is served again")
    validate_equals(openbao.rest_status_code("basic-secret/restartcheck", root_token), "200", "Previously stored secret must be served again after the auto-unseal")


@mark.p2
def test_openbao_unseal_material_is_immutable(request: FixtureRequest):
    """Test that the unseal-key generation secret is immutable and tamper-proof.

    The current unseal generation secret is marked immutable, carries the
    expected unseal-key material, and rejects an attempt to patch its contents,
    protecting the unseal material from tampering.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - resolve the current unseal generation secret
        - confirm the generation secret is immutable
        - confirm the generation secret carries unseal-key material
        - attempt to patch the immutable secret and confirm rejection
        - Teardown: clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Resolving the current unseal generation secret")
    gen_secret = openbao.get_current_gen_secret_name()
    validate_not_equals(gen_secret, "", "Must resolve a current unseal generation secret")

    get_logger().log_test_case_step("Confirming the generation secret is immutable")
    validate_equals(openbao.is_gen_secret_immutable(gen_secret), True, "Unseal generation secret must be immutable")

    get_logger().log_test_case_step("Confirming the generation secret carries unseal-key material")
    validate_list_contains("keys", openbao.get_gen_secret_keys(gen_secret), "Unseal generation secret must carry the unseal keys payload")

    get_logger().log_test_case_step("Attempting to patch the immutable secret and confirming rejection")
    validate_equals(openbao.patch_gen_secret_rejected(gen_secret), True, "Patching the immutable unseal secret must be rejected")


@mark.p2
def test_openbao_unexpected_helm_override_tolerated(request: FixtureRequest):
    """Test that an unexpected helm override does not corrupt the application.

    StarlingX stores an unknown chart value as an inert user override. Applying
    one and re-applying must leave OpenBao settled at applied and still serving,
    not stuck or corrupt, and clearing the override and re-applying keeps it
    applied.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - apply an unexpected helm override and re-apply, waiting for it to settle
        - confirm the application settles to applied and OpenBao still serves
        - clear the override and re-apply, confirming it stays applied
        - Teardown: delete the override, re-apply and clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    unexpected_override = "server.notARealValue.bogus=12345"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        SystemHelmOverrideKeywords(ssh).delete_system_helm_override(APP_NAME, APP_NAME, NAMESPACE)
        SystemApplicationApplyKeywords(ssh).system_application_apply(APP_NAME)
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Applying an unexpected helm override and re-applying until it settles")
    helm = SystemHelmOverrideKeywords(ssh_connection)
    helm.update_helm_override_via_set(unexpected_override, APP_NAME, APP_NAME, NAMESPACE)
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)

    get_logger().log_test_case_step("Confirming the application settled to applied and OpenBao still serves")
    validate_equals(SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(APP_NAME).get_status(), "applied", "Application must settle to applied with the unexpected override, not a corrupt state")
    validate_equals(openbao.rest_health_trusts_ca(), True, "OpenBao must still serve its health endpoint with the unexpected override applied")

    get_logger().log_test_case_step("Clearing the override and re-applying, confirming it stays applied")
    helm.delete_system_helm_override(APP_NAME, APP_NAME, NAMESPACE)
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)
    validate_equals(SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(APP_NAME).get_status(), "applied", "Application must stay applied after clearing the unexpected override")


@mark.p2
def test_openbao_unseal_pointer_recovers_after_corruption(request: FixtureRequest):
    """Test that a deleted unseal pointer is recoverable from backup.

    The mutable ``openbao-unseal-current`` pointer is only needed at unseal
    time, so an already-unsealed server keeps serving secrets after the pointer
    is deleted; the pointer is then recovered by restoring it from a backup.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - seed a secret, then back up and delete the unseal-current pointer secret
        - confirm the already-unsealed server keeps serving secrets without the pointer
        - restore the pointer from backup and confirm it is present again
        - Teardown: restore the pointer if it is still missing and clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    pointer = "openbao-unseal-current"
    backup = {"path": None}

    def cleanup():
        get_logger().log_teardown_step("Restoring the unseal pointer if missing and cleaning up the OpenBao environment")
        try:
            if backup["path"] and not openbao.is_secret_present(pointer):
                openbao.restore_secret_yaml(backup["path"])
        finally:
            cleanup_openbao_environment(ssh_connection)

    request.addfinalizer(cleanup)
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Seeding a secret, backing up and deleting the unseal-current pointer")
    root_token = openbao.get_root_token()
    openbao.create_secret_rest("basic-secret/pointercheck", {"k": "v"}, root_token)
    backup["path"] = openbao.backup_secret_yaml(pointer)
    openbao.kubectl_delete.delete_resource("secret", pointer, NAMESPACE)

    get_logger().log_test_case_step("Confirming the already-unsealed server keeps serving secrets without the pointer")
    validate_equals(openbao.rest_status_code("basic-secret/pointercheck", root_token), "200", "Server must keep serving secrets while already unsealed, even with the pointer deleted")

    get_logger().log_test_case_step("Restoring the pointer from backup and confirming it is present again")
    openbao.restore_secret_yaml(backup["path"])
    validate_equals_with_retry(lambda: openbao.is_secret_present(pointer), True, "The unseal-current pointer must be present again after restore from backup", timeout=120, polling_sleep_time=10)


@mark.p2
def test_openbao_host_api_not_reachable_from_pod(request: FixtureRequest):
    """Test that the host OpenBao API is isolated from in-cluster pods.

    The host OpenBao service listens on the management network. From inside the
    OpenBao server pod, the in-cluster app service is reachable (probe control),
    while the host management-network API is blocked by network policy. The host
    service itself is confirmed active and unsealed from the platform side.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - confirm the host OpenBao service is active and unsealed from the platform
        - confirm the probe pod can reach the in-cluster OpenBao app service
        - confirm the same pod cannot reach the host management-network API
        - Teardown: clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Confirming the host OpenBao service is active and unsealed from the platform")
    validate_equals(openbao.is_host_service_active(), True, "Host OpenBao service must be active on the platform side")
    validate_str_contains(openbao.host_bao_status_with_ca(), "false", "Host OpenBao must be unsealed on the platform side")

    get_logger().log_test_case_step("Confirming the probe pod can reach the in-cluster OpenBao app service")
    validate_equals(openbao.is_app_service_reachable_from_server_pod(), True, "Probe pod must reach the in-cluster OpenBao app service")

    get_logger().log_test_case_step("Confirming the probe pod cannot reach the host management-network API")
    validate_equals(openbao.host_api_reachable_from_pod(), False, "In-cluster pods must not be able to reach the host management-network API")


@mark.p2
def test_openbao_server_pod_recovery_manager_reunseals(request: FixtureRequest):
    """Test that the manager re-unseals a deleted server pod with no major errors.

    Deleting an OpenBao server pod causes the manager to detect the replacement
    and unseal it; the recreated server returns to a ready, unsealed state and
    the manager log records no FATAL/panic during the recovery.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - delete the running server pod
        - confirm the server pod is recreated as a new instance (new UID) and is ready
        - confirm the manager re-unseals the replacement server
        - confirm the manager log records no FATAL or panic during recovery
        - Teardown: clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Deleting the running server pod")
    server_pod = openbao.get_server_pod_name()
    old_server_uid = openbao.get_pod_uid(server_pod)
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(server_pod, namespace=NAMESPACE)

    get_logger().log_test_case_step("Confirming the server pod is recreated as a new instance and is ready")
    validate_equals_with_retry(lambda: openbao.has_pod_restarted(server_pod, old_server_uid), True, "Server pod must be recreated with a new UID and become ready", timeout=300, polling_sleep_time=10)

    get_logger().log_test_case_step("Confirming the manager re-unseals the replacement server")
    validate_equals(openbao.wait_for_unseal(), True, "Manager must re-unseal the recreated server pod with no manual step")

    get_logger().log_test_case_step("Confirming the manager log records no FATAL or panic during recovery")
    validate_equals(openbao.manager_log_has_major_errors(), False, "Manager log must not contain FATAL or panic during server pod recovery")


@mark.p2
def test_openbao_manager_pod_recovery_resumes_watch(request: FixtureRequest):
    """Test that a deleted manager pod restarts and resumes seal-watching.

    Deleting the OpenBao manager pod causes it to be recreated; the new manager
    resumes its perpetual seal-watch with no FATAL/panic, and the running server
    stays unsealed across the manager restart.

    Test Steps:
        - set up the OpenBao application (applied, unsealed, configured)
        - delete the manager pod
        - confirm the manager pod is recreated as a new instance (new UID) and is ready
        - confirm the new manager restarts its run loop and resumes watching
        - confirm the server stayed unsealed and the manager logged no errors
        - Teardown: clean up the OpenBao environment

    Args:
        request (FixtureRequest): Pytest request fixture for teardown management.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Deleting the manager pod")
    manager_pod = openbao.get_manager_pod_name()
    validate_not_equals(manager_pod, "", "A running OpenBao manager pod must exist before deletion")
    old_manager_uid = openbao.get_pod_uid(manager_pod)
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(manager_pod, namespace=NAMESPACE)

    get_logger().log_test_case_step("Confirming the manager pod is recreated as a new instance and is ready")
    validate_equals_with_retry(lambda: openbao.has_pod_restarted(manager_pod, old_manager_uid), True, "Manager pod must be recreated with a new UID and become ready", timeout=300, polling_sleep_time=10)
    validate_not_equals(openbao.get_pod_uid(manager_pod), old_manager_uid, "Recovered manager must be a different pod instance from the deleted one")

    get_logger().log_test_case_step("Confirming the new manager restarts its run loop and resumes watching")
    validate_equals_with_retry(lambda: openbao.manager_log_contains("Run loop starting"), True, "New manager must restart its run loop and resume watching OpenBao after recovery", timeout=180, polling_sleep_time=10)

    get_logger().log_test_case_step("Confirming the server stayed unsealed and the manager logged no errors")
    validate_equals(openbao.rest_health_trusts_ca(), True, "Server must stay unsealed across the manager pod restart")
    validate_equals(openbao.manager_log_has_major_errors(), False, "Recovered manager log must not contain FATAL or panic")

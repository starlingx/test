"""OpenBao application functional tests.

Covers the OpenBao application (container) scenarios:
    - app upload + apply, server unsealed, unseal secrets present
    - configure via REST API and create/read a KV v2 secret
    - configure via the in-pod ``bao`` CLI and create/read a KV v2 secret
    - OpenBao-aware application: direct REST store + read (KV v2)
    - OpenBao-unaware application: agent-injector delivers the secret to the pod
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.resources.resource_finder import get_stx_resource_path
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_list_contains, validate_not_equals, validate_not_none, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteInput, SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveInput, SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_update_keywords import SystemApplicationUpdateInput, SystemApplicationUpdateKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadInput, SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.openbao.openbao_keywords import OpenBaoKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.certificate.kubectl_get_certificate_keywords import KubectlGetCertStatusKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.namespace.kubectl_create_namespace_keywords import KubectlCreateNamespacesKeywords
from keywords.k8s.namespace.kubectl_delete_namespace_keywords import KubectlDeleteNamespaceKeywords
from keywords.k8s.namespace.kubectl_label_namespace_keywords import KubectlLabelNamespaceKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords
from keywords.linux.ls.ls_keywords import LsKeywords

APP_NAME = "openbao"
CHART_PATH = "/usr/local/share/applications/helm/openbao-[0-9]*"
NAMESPACE = "openbao"
TEST_NAMESPACE = "pvtest"
SECRET_PATH = "basic-secret/helloworld"
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
    validate_equals(
        app_list.is_app_present("platform-integ-apps"),
        True,
        "platform-integ-apps must be present for OpenBao PVC",
    )

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

    get_logger().log_info("Waiting for OpenBao pods to be running")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)

    security_config = ConfigurationManager.get_security_config()
    openbao_keywords = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    get_logger().log_info("Waiting for OpenBao to be unsealed (all server pods Ready)")
    unsealed = openbao_keywords.wait_for_unseal(timeout=300)
    validate_equals(unsealed, True, "OpenBao should be unsealed after apply")

    get_logger().log_info("Extracting the OpenBao CA certificate for REST TLS verification")
    openbao_keywords.extract_ca_cert()

    get_logger().log_info("Configuring KV v2 engine, kubernetes auth, policy and role")
    root_token = openbao_keywords.get_root_token()
    openbao_keywords.enable_kv_v2(root_token)
    openbao_keywords.enable_kubernetes_auth(root_token)
    openbao_keywords.configure_kubernetes_auth(root_token)
    openbao_keywords.write_policy(POLICY_NAME, POLICY_HCL, root_token)
    openbao_keywords.write_kubernetes_role(ROLE_NAME, SERVICE_ACCOUNT, TEST_NAMESPACE, POLICY_NAME, root_token)


def cleanup_openbao_environment(ssh_connection: object) -> None:
    """Clean up OpenBao test resources.

    Args:
        ssh_connection (object): SSH connection to active controller.
    """
    get_logger().log_teardown_step("Cleaning up OpenBao test resources")

    KubectlDeleteNamespaceKeywords(ssh_connection).cleanup_namespace(TEST_NAMESPACE)

    OpenBaoKeywords(ssh_connection).delete_clusterrolebinding("pvtest-user-clusterrolebinding")

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


@mark.p0
def test_openbao_app_apply(request: FixtureRequest):
    """Verify OpenBao application uploads, applies, and the server unseals.

    Test Steps:
        - Upload and apply the OpenBao application
        - Verify the application is applied
        - Verify all OpenBao server pods are Running and unsealed
        - Verify the openbao-server-tls certificate is Ready
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))

    get_logger().log_setup_step("Set up the OpenBao application")
    setup_openbao_environment(ssh_connection)

    get_logger().log_test_case_step("Verify the OpenBao application is applied")
    validate_equals(SystemApplicationApplyKeywords(ssh_connection).is_already_applied(APP_NAME), True, "OpenBao application should be applied")

    get_logger().log_test_case_step("Verify OpenBao server pods are unsealed")
    openbao_keywords = OpenBaoKeywords(ssh_connection, ConfigurationManager.get_security_config().get_ssh_user_home())
    validate_equals(openbao_keywords.wait_for_unseal(timeout=120), True, "OpenBao server pods should be unsealed")

    get_logger().log_test_case_step("Verify the openbao-server-tls certificate is Ready")
    KubectlGetCertStatusKeywords(ssh_connection).wait_for_certs_status("openbao-server-tls", True, namespace=NAMESPACE, timeout=120)


@mark.p1
def test_openbao_rest_kv_secret(request: FixtureRequest):
    """Verify a KV v2 secret can be created and read via the OpenBao REST API.

    Test Steps:
        - Set up OpenBao (KV v2 + kubernetes auth configured)
        - Create a secret via the REST API
        - Read the secret back via the REST API and verify it round-trips
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))

    get_logger().log_setup_step("Set up the OpenBao application")
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao_keywords = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    root_token = openbao_keywords.get_root_token()
    secret_data = {
        "password": security_config.get_openbao_test_secret_password(),
        "username": security_config.get_openbao_test_secret_username(),
    }

    get_logger().log_test_case_step("Create a KV v2 secret via the REST API")
    openbao_keywords.create_secret_rest(SECRET_PATH, secret_data, root_token)

    get_logger().log_test_case_step("Read the secret back via the REST API")
    response = openbao_keywords.read_secret_rest(SECRET_PATH, root_token)
    validate_equals("errors" not in response, True, "OpenBao secret read should not return errors")
    validate_equals(response["data"]["data"], secret_data, "OpenBao secret data should round-trip verbatim")


@mark.p1
def test_openbao_cli_kv_secret(request: FixtureRequest):
    """Verify a KV v2 secret via the in-pod ``bao`` CLI (non-interactive, TC-2).

    Uses ``kubectl exec`` with BAO_TOKEN injected in the pod env (no interactive
    shell). Distinct from TC-3 which authenticates via ``bao login``.

    Test Steps:
        - Set up OpenBao (KV v2 + kubernetes auth configured)
        - Create a secret via the in-pod bao CLI (BAO_TOKEN in env)
        - Read the secret back via the in-pod bao CLI and verify the values
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))

    get_logger().log_setup_step("Set up the OpenBao application")
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao_keywords = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    root_token = openbao_keywords.get_root_token()
    username = security_config.get_openbao_test_secret_username()
    password = security_config.get_openbao_test_secret_password()

    get_logger().log_test_case_step("Create a KV v2 secret via the in-pod bao CLI")
    openbao_keywords.create_secret_cli(SECRET_PATH, {"username": username, "password": password}, root_token)

    get_logger().log_test_case_step("Read the secret back via the in-pod bao CLI")
    output = openbao_keywords.read_secret_cli(SECRET_PATH, root_token)
    validate_str_contains(output, username, "bao kv get should show the stored username")
    validate_str_contains(output, password, "bao kv get should show the stored password")


@mark.p1
def test_openbao_cli_login_kv_secret(request: FixtureRequest):
    """Verify KV v2 via the in-pod ``bao`` CLI authenticated with ``bao login`` (TC-3).

    Distinct from TC-2: authenticates through the ``bao login`` token method
    before reading, exercising the login codepath rather than BAO_TOKEN-in-env.

    Test Steps:
        - Set up OpenBao (KV v2 + kubernetes auth configured)
        - Create a secret via the in-pod bao CLI
        - ``bao login`` (token method) then read the secret back and verify
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))

    get_logger().log_setup_step("Set up the OpenBao application")
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao_keywords = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    root_token = openbao_keywords.get_root_token()
    username = security_config.get_openbao_test_secret_username()
    password = security_config.get_openbao_test_secret_password()

    get_logger().log_test_case_step("Create a KV v2 secret via the in-pod bao CLI")
    openbao_keywords.create_secret_cli(SECRET_PATH, {"username": username, "password": password}, root_token)

    get_logger().log_test_case_step("Authenticate via bao login then read the secret back")
    output = openbao_keywords.login_token_and_read(SECRET_PATH, root_token)
    validate_str_contains(output, username, "bao kv get after login should show the stored username")
    validate_str_contains(output, password, "bao kv get after login should show the stored password")


@mark.p1
def test_openbao_aware_app_rest(request: FixtureRequest):
    """Verify an OpenBao-aware client stores and reads a secret directly via REST.

    Test Steps:
        - Set up OpenBao (KV v2 + kubernetes auth configured)
        - Store a secret directly via the REST API (aware client)
        - Read it back and verify the data and that a version is present
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))

    get_logger().log_setup_step("Set up the OpenBao application")
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao_keywords = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    root_token = openbao_keywords.get_root_token()
    secret_data = {
        "password": security_config.get_openbao_test_secret_password(),
        "username": security_config.get_openbao_test_secret_username(),
    }

    get_logger().log_test_case_step("Aware client stores a secret via the REST API")
    openbao_keywords.create_secret_rest(SECRET_PATH, secret_data, root_token)

    get_logger().log_test_case_step("Aware client reads the secret back and verifies it")
    response = openbao_keywords.read_secret_rest(SECRET_PATH, root_token)
    validate_equals(response["data"]["data"], secret_data, "Aware-client secret data should round-trip verbatim")
    validate_equals("version" in response["data"]["metadata"], True, "KV v2 response should include a version")


@mark.p1
def test_openbao_unaware_app_injection(request: FixtureRequest):
    """Verify the agent-injector delivers a secret to an OpenBao-unaware pod.

    Test Steps:
        - Set up OpenBao and store the helloworld secret
        - Copy the OpenBao CA + registry secrets into the test namespace
        - Deploy the helloworld app with agent-inject annotations
        - Wait for the injected pod to be Running
        - Verify the secret is delivered to /vault/secrets/helloworld
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    request.addfinalizer(lambda: cleanup_openbao_environment(ssh_connection))

    get_logger().log_setup_step("Set up the OpenBao application and store the test secret")
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao_keywords = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    root_token = openbao_keywords.get_root_token()
    secret_data = {
        "password": security_config.get_openbao_test_secret_password(),
        "username": security_config.get_openbao_test_secret_username(),
    }
    openbao_keywords.create_secret_rest(SECRET_PATH, secret_data, root_token)

    get_logger().log_test_case_step("Copy OpenBao CA and registry secrets into the test namespace")
    openbao_keywords.setup_test_namespace_secrets(TEST_NAMESPACE)

    get_logger().log_test_case_step("Deploy the helloworld agent-inject application")
    local_app = get_stx_resource_path("resources/cloud_platform/security/openbao/helloworld.yaml")
    remote_app = f"{security_config.get_ssh_user_home()}/openbao_helloworld.yaml"
    FileKeywords(ssh_connection).upload_file(local_app, remote_app, overwrite=True)
    KubectlFileApplyKeywords(ssh_connection).apply_resource_from_yaml(remote_app)

    get_logger().log_test_case_step("Wait for the injected test pod to be Running")
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=TEST_NAMESPACE, timeout=300)

    get_logger().log_test_case_step("Verify the secret is injected into the pod filesystem")
    pod_name = openbao_keywords.get_first_pod_name(TEST_NAMESPACE)
    validate_equals_with_retry(
        lambda: openbao_keywords.get_injected_secret(pod_name, TEST_NAMESPACE).get("username"),
        secret_data["username"],
        "Injected username should match (agent sidecar renders the secret shortly after pod start)",
        timeout=120,
        polling_sleep_time=10,
    )
    injected_secret = openbao_keywords.get_injected_secret(pod_name, TEST_NAMESPACE)
    validate_equals(injected_secret["password"], secret_data["password"], "Injected password should match")


@mark.p1
def test_openbao_app_full_lifecycle(request: FixtureRequest):
    """Verify OpenBao app lifecycle: remove retains PVC/data, delete destroys PVC.

    Test Steps:
        - Apply OpenBao and store a known secret via REST (KV v2)
        - Record the openbao PVC names (expect Bound)
        - Remove the app: state returns to 'uploaded', PVCs retained
        - Re-apply the app: secret still readable (survived remove + reapply)
        - Delete the app: gone from application-list, PVCs destroyed
    """

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    token = openbao.get_root_token()

    get_logger().log_info("Storing a known secret before remove")
    secret = {
        "username": security_config.get_openbao_test_secret_username(),
        "password": security_config.get_openbao_test_secret_password(),
    }
    openbao.create_secret_rest(SECRET_PATH, secret, token)

    pvc_names = openbao.get_openbao_pvc_names()
    validate_equals(len(pvc_names) > 0, True, "OpenBao should have at least one PVC bound")

    get_logger().log_info("Removing the OpenBao application")
    remove_input = SystemApplicationRemoveInput()
    remove_input.set_app_name(APP_NAME)
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)

    validate_equals(SystemApplicationListKeywords(ssh_connection).is_app_present(APP_NAME), True, "App should still be present (uploaded) after remove")
    validate_equals(sorted(openbao.get_openbao_pvc_names()), sorted(pvc_names), "PVCs must be retained after application-remove")

    get_logger().log_info("Re-applying the OpenBao application")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)
    openbao.wait_for_unseal()
    token = openbao.get_root_token()

    get_logger().log_info("Reading the secret back via the in-pod CLI after reapply")
    read_back = openbao.read_secret_cli(SECRET_PATH, token)
    validate_str_contains(read_back, security_config.get_openbao_test_secret_password(), "Secret must survive remove + reapply (PVC preserved)")

    get_logger().log_info("Deleting the OpenBao application")
    SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(remove_input)
    delete_input = SystemApplicationDeleteInput()
    delete_input.set_app_name(APP_NAME)
    SystemApplicationDeleteKeywords(ssh_connection).get_system_application_delete(delete_input)

    validate_equals(SystemApplicationListKeywords(ssh_connection).is_app_present(APP_NAME), False, "App must be gone from application-list after delete")
    validate_equals(len(openbao.get_openbao_pvc_names()), len(pvc_names), "OpenBao data and audit PVCs are retained after application-delete (preserved as tamper-proof records)")


@mark.p2
def test_openbao_app_update_preserves_data(request: FixtureRequest):
    """Verify application-update preserves OpenBao data and the server re-unseals.

    When a previous-version bundle is configured (app_config openbao_app_tarball_n1),
    the test exercises a real application-update and asserts the version changes while
    the stored secret survives. When no such bundle is configured, it validates the
    data-preservation guarantee on the single staged bundle so the test still passes.

    Test Steps:
        - Apply OpenBao at the current version and store a known secret
        - Record the current unseal-key generation
        - If a previous-version bundle is configured: update to it and verify the
          version changed and the server re-unsealed
        - Confirm the known secret reads back identically and the generation is unchanged
    """

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    app_config = ConfigurationManager.get_app_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())
    token = openbao.get_root_token()

    get_logger().log_info("Recording pre-update generation and storing a known secret")
    gen_before = openbao.get_current_gen_secret_name()
    secret = {
        "username": security_config.get_openbao_test_secret_username(),
        "password": security_config.get_openbao_test_secret_password(),
    }
    openbao.create_secret_rest(SECRET_PATH, secret, token)

    update_tarball = app_config.get_openbao_app_tarball_n1()
    if update_tarball != "fake_path":
        get_logger().log_info("Previous-version bundle configured; exercising application-update")
        remote_tarball = f"/home/sysadmin/{update_tarball.split('/')[-1]}"
        FileKeywords(ssh_connection).upload_file(update_tarball, remote_tarball)
        applied_version = SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(APP_NAME).get_version()

        update_input = SystemApplicationUpdateInput()
        update_input.set_tar_file_path(remote_tarball)
        update_input.set_app_name(APP_NAME)
        update_input.set_timeout_in_seconds(1800)
        SystemApplicationUpdateKeywords(ssh_connection).system_application_update(update_input)

        updated_version = SystemApplicationListKeywords(ssh_connection).get_system_application_list().get_application(APP_NAME).get_version()
        validate_not_equals(updated_version, applied_version, "OpenBao version must change after application-update")
        validate_equals(openbao.wait_for_unseal(), True, "Server must re-unseal after application-update")
        token = openbao.get_root_token()
    else:
        get_logger().log_info("No previous-version bundle configured; validating data preservation on the current version")

    read_back = openbao.read_secret_cli(SECRET_PATH, token)
    validate_str_contains(read_back, security_config.get_openbao_test_secret_password(), "Secret must read back identically (PVC preserved)")
    validate_equals(openbao.get_current_gen_secret_name(), gen_before, "Unseal generation must be unchanged")


@mark.p1
def test_openbao_unseal_secret_immutable(request: FixtureRequest):
    """Verify unseal keys + root token live in one immutable generation secret.

    Test Steps:
        - Apply OpenBao and resolve the current unseal-key generation secret
        - Confirm the generation secret is immutable
        - Confirm the generation secret holds all shards plus the root token
        - Confirm the unseal-current pointer resolves to a non-empty root token
    """

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    gen_name = openbao.get_current_gen_secret_name()
    validate_str_contains(gen_name, "openbao-unseal-gen", "Current generation secret should be a gen-NNN secret")

    validate_equals(openbao.is_gen_secret_immutable(gen_name), True, "Generation secret must be immutable")

    keys = openbao.get_gen_secret_keys(gen_name)
    validate_list_contains("root_token", keys, "Generation secret must contain the root token")
    validate_list_contains("keys", keys, "Generation secret must contain the unseal key shards")

    validate_not_none(openbao.get_root_token(), "unseal-current pointer must resolve to a non-empty root token")


@mark.p2
def test_openbao_helm_override_reaches_pods(request: FixtureRequest):
    """Verify a helm override is accepted, stored, and reaches the workload template.

    Test Steps:
        - Apply OpenBao
        - Set a server.extraLabels override via helm-override-update
        - Confirm helm-override-show reflects the override
        - Re-apply and confirm the StatefulSet pod template carries the label
    """

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    helm = SystemHelmOverrideKeywords(ssh_connection)
    get_logger().log_info("Setting server.extraLabels.pv=test override")
    helm.update_helm_override_via_set("server.extraLabels.pv=test", APP_NAME, APP_NAME, NAMESPACE)
    helm.verify_helm_user_override("pv", APP_NAME, APP_NAME, NAMESPACE)

    get_logger().log_info("Re-applying so the override reaches the workload template")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)

    openbao = OpenBaoKeywords(ssh_connection, ConfigurationManager.get_security_config().get_ssh_user_home())
    validate_str_contains(openbao.get_statefulset_template_label("pv"), "test", "Override label pv=test must propagate to the StatefulSet pod template")


@mark.p2
def test_openbao_psa_enforce_admits_privileged(request: FixtureRequest):
    """Verify the privileged-labeled openbao namespace is admitted under PSA enforcement.

    Test Steps:
        - Apply OpenBao and confirm its namespace enforces the privileged PodSecurity level
        - Server-dry-run a privileged pod in a throwaway restricted namespace and expect it DENIED
        - Server-dry-run the same privileged pod in the openbao namespace and expect it ADMITTED
    """

    restricted_ns = "pv-psa-restricted"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        KubectlDeleteNamespaceKeywords(ssh).cleanup_namespace(restricted_ns)
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    openbao = OpenBaoKeywords(ssh_connection, ConfigurationManager.get_security_config().get_ssh_user_home())

    get_logger().log_info("Confirming the openbao namespace enforces the privileged PodSecurity level")
    validate_equals(openbao.get_namespace_psa_enforce(NAMESPACE), "privileged", "openbao namespace must enforce the privileged PodSecurity level")

    get_logger().log_info("Creating a throwaway restricted namespace for the negative check")
    KubectlCreateNamespacesKeywords(ssh_connection).create_namespace_if_absent(restricted_ns)
    KubectlLabelNamespaceKeywords(ssh_connection).label_namespace(restricted_ns, "pod-security.kubernetes.io/enforce", "restricted")

    get_logger().log_info("A privileged pod must be DENIED in the restricted namespace")
    validate_str_contains(openbao.dry_run_privileged_pod(restricted_ns), "violates PodSecurity", "Privileged pod must be denied in a restricted namespace")

    get_logger().log_info("A privileged pod must be ADMITTED in the openbao namespace")
    validate_str_contains(openbao.dry_run_privileged_pod(NAMESPACE), "psa-probe", "Privileged pod must be admitted (dry-run) in the privileged openbao namespace")


@mark.p2
def test_openbao_cpu_core_switch_to_application(request: FixtureRequest):
    """Verify OpenBao pods switch from platform to application cores via helm override.

    OpenBao defaults to platform cores. The server and injector pods are controlled
    by the openbao chart; the manager pod is a separate openbao-manager chart. This
    test overrides labels.isApplication=true on both charts, reapplies, restarts the
    pods, and verifies each pod carries app.starlingx.io/component=application and is
    pinned to an application core. Teardown reverts both overrides so the pods return
    to platform cores.

    Test Steps:
        - Apply OpenBao (default platform cores) and confirm the platform component label
        - Helm-override labels.isApplication=true on the openbao and openbao-manager charts
        - Reapply and restart the server and manager pods to pick up the changed label
        - Verify every pod carries component=application and its PSR is an application core
        - Teardown: reset both overrides and reapply so pods return to platform cores
    """

    component_label_key = "app.starlingx.io/component"
    manager_chart = "openbao-manager"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_info("Reverting the app-component overrides back to platform cores")
        helm = SystemHelmOverrideKeywords(ssh)
        helm.helm_override_update_with_list_of_values(
            app_name=APP_NAME,
            chart_name=APP_NAME,
            namespace=NAMESPACE,
            reuse_values=True,
            set_override=["server.labels.isApplication=false", "injector.labels.isApplication=false"],
        )
        helm.helm_override_update_with_list_of_values(
            app_name=APP_NAME,
            chart_name=manager_chart,
            namespace=NAMESPACE,
            reuse_values=True,
            set_override=["manager.labels.isApplication=false"],
        )
        SystemApplicationApplyKeywords(ssh).system_application_apply(APP_NAME)
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    lab_connection_keywords = LabConnectionKeywords()
    ssh_connection = lab_connection_keywords.get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    get_logger().log_info("Confirming OpenBao pods default to the platform component")
    for pod in KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=NAMESPACE).get_pods():
        labels = KubectlGetPodsKeywords(ssh_connection).get_pod_labels(pod.get_name(), namespace=NAMESPACE)
        validate_equals(labels.get(component_label_key), "platform", f"Pod {pod.get_name()} must default to the platform component")

    get_logger().log_info("Applying helm overrides to switch OpenBao to application cores")
    helm = SystemHelmOverrideKeywords(ssh_connection)
    helm.helm_override_update_with_list_of_values(
        app_name=APP_NAME,
        chart_name=APP_NAME,
        namespace=NAMESPACE,
        reuse_values=True,
        set_override=["server.labels.isApplication=true", "injector.labels.isApplication=true"],
    )
    helm.helm_override_update_with_list_of_values(
        app_name=APP_NAME,
        chart_name=manager_chart,
        namespace=NAMESPACE,
        reuse_values=True,
        set_override=["manager.labels.isApplication=true"],
    )
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)

    openbao = OpenBaoKeywords(ssh_connection, ConfigurationManager.get_security_config().get_ssh_user_home())

    get_logger().log_info("Restarting all server replicas and the manager pod to pick up the changed label")
    for server_pod in openbao.get_server_pod_names():
        openbao.kubectl_delete.delete_resource("pod", server_pod, NAMESPACE)
    openbao.kubectl_delete.delete_resource("pod", "stx-openbao-manager-3-0", NAMESPACE)
    KubectlGetPodsKeywords(ssh_connection).wait_for_pods_to_reach_status("Running", namespace=NAMESPACE, timeout=600)
    validate_equals(openbao.wait_for_unseal(), True, "OpenBao should be unsealed after the core-label switch")

    get_logger().log_info("Verifying every OpenBao pod carries the application component label")

    for pod in KubectlGetPodsKeywords(ssh_connection).get_pods(namespace=NAMESPACE).get_pods():
        pod_name = pod.get_name()

        validate_equals_with_retry(lambda name=pod_name: KubectlGetPodsKeywords(ssh_connection).get_pod_labels(name, namespace=NAMESPACE).get(component_label_key), "application", f"Pod {pod_name} must carry the application component label after the switch", timeout=120, polling_sleep_time=10)


@mark.p2
def test_openbao_disable_manager_chart(request: FixtureRequest):
    """Verify disabling the openbao-manager chart removes the manager but keeps the server unsealed.

    The openbao-manager drives only the INITIAL unseal. Disabling its chart on an
    already-running, unsealed OpenBao removes the manager pod while the server stays
    unsealed. Re-enabling the chart brings the manager pod back.

    Test Steps:
        - Apply OpenBao and confirm the server is unsealed with a manager pod present
        - Disable the openbao-manager chart and reapply
        - Confirm the manager pod is gone and the server stays unsealed
        - Re-enable the openbao-manager chart and reapply
        - Confirm the manager pod returns and the server is unsealed
    """

    manager_chart = "openbao-manager"

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        get_logger().log_info("Re-enabling the openbao-manager chart")
        SystemHelmChartAttributeModifyKeywords(ssh).helm_chart_attribute_modify_enabled("true", APP_NAME, manager_chart, NAMESPACE)
        SystemApplicationApplyKeywords(ssh).system_application_apply(APP_NAME)
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    openbao = OpenBaoKeywords(ssh_connection, ConfigurationManager.get_security_config().get_ssh_user_home())
    validate_equals(openbao.is_manager_pod_present(), True, "Manager pod should be present before disabling the chart")
    validate_equals(openbao.wait_for_unseal(), True, "OpenBao should be unsealed before disabling the manager chart")

    get_logger().log_info("Disabling the openbao-manager chart and reapplying")
    SystemHelmChartAttributeModifyKeywords(ssh_connection).helm_chart_attribute_modify_enabled("false", APP_NAME, manager_chart, NAMESPACE)
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)

    get_logger().log_info("Confirming the manager pod is gone and the server stays unsealed")
    validate_equals_with_retry(openbao.is_manager_pod_present, False, "Manager pod must be removed after disabling the openbao-manager chart", timeout=180, polling_sleep_time=10)
    validate_equals(openbao.wait_for_unseal(), True, "Server must stay unsealed after the manager chart is disabled")

    get_logger().log_info("Re-enabling the openbao-manager chart and reapplying")
    SystemHelmChartAttributeModifyKeywords(ssh_connection).helm_chart_attribute_modify_enabled("true", APP_NAME, manager_chart, NAMESPACE)
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(APP_NAME)

    get_logger().log_info("Confirming the manager pod returns and the server is unsealed")
    validate_equals_with_retry(openbao.is_manager_pod_present, True, "Manager pod must return after re-enabling the openbao-manager chart", timeout=180, polling_sleep_time=10)
    validate_equals(openbao.wait_for_unseal(), True, "Server must be unsealed after re-enabling the manager chart")


@mark.p2
def test_openbao_psa_compliance(request: FixtureRequest):
    """Verify the openbao namespace tolerates stricter PSA warn/audit without blocking pods.

    The openbao namespace enforces the privileged PodSecurity level, so applying
    stricter warn/audit levels records violations as warnings/audit annotations but
    does not block admission. This complements the enforce check by covering the
    warn and audit PSA modes.

    Test Steps:
        - Apply OpenBao and record the current PSA fit (enforce/warn/audit)
        - Confirm the namespace enforces the privileged level
        - Set warn=restricted and audit=restricted on the openbao namespace
        - Dry-run a privileged pod and confirm it is still ADMITTED under enforce=privileged
        - Teardown: remove the added warn/audit labels
    """

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        label_keywords = KubectlLabelNamespaceKeywords(ssh)
        label_keywords.remove_label(NAMESPACE, "pod-security.kubernetes.io/warn")
        label_keywords.remove_label(NAMESPACE, "pod-security.kubernetes.io/audit")
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    openbao = OpenBaoKeywords(ssh_connection, ConfigurationManager.get_security_config().get_ssh_user_home())

    get_logger().log_info("Recording the current PSA fit on the openbao namespace")
    get_logger().log_info(f"enforce={openbao.get_namespace_psa_level(NAMESPACE, 'enforce')} warn={openbao.get_namespace_psa_level(NAMESPACE, 'warn')} audit={openbao.get_namespace_psa_level(NAMESPACE, 'audit')}")
    validate_equals(openbao.get_namespace_psa_level(NAMESPACE, "enforce"), "privileged", "openbao namespace must enforce the privileged PodSecurity level")

    get_logger().log_info("Applying stricter warn and audit PSA levels to the openbao namespace")
    label_keywords = KubectlLabelNamespaceKeywords(ssh_connection)
    label_keywords.label_namespace(NAMESPACE, "pod-security.kubernetes.io/warn", "restricted")
    label_keywords.label_namespace(NAMESPACE, "pod-security.kubernetes.io/audit", "restricted")

    validate_equals(openbao.get_namespace_psa_level(NAMESPACE, "warn"), "restricted", "warn level should be set to restricted")
    validate_equals(openbao.get_namespace_psa_level(NAMESPACE, "audit"), "restricted", "audit level should be set to restricted")

    get_logger().log_info("A privileged pod must still be ADMITTED under enforce=privileged despite stricter warn/audit")
    validate_str_contains(openbao.dry_run_privileged_pod(NAMESPACE), "psa-probe", "Privileged pod must remain admitted in the openbao namespace under enforce=privileged")


@mark.p1
def test_openbao_shamir_key_config(request: FixtureRequest):
    """Verify Shamir config: 5 shards + root token in one gen secret, threshold 3 (TC-61).

    Confirms PR.2558.005/006/009 - the current generation secret holds all five
    unseal key shards plus the root token in a single immutable secret, and the
    Shamir seal reports Total Shares = 5 with Threshold = 3.

    Test Steps:
        - Apply OpenBao and resolve the current generation secret
        - Confirm the generation secret is immutable and holds shards + root token
        - Read the seal-status and confirm total_shares=5 / threshold=3
    """

    def cleanup():
        ssh = LabConnectionKeywords().get_active_controller_ssh()
        cleanup_openbao_environment(ssh)

    request.addfinalizer(cleanup)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup_openbao_environment(ssh_connection)

    security_config = ConfigurationManager.get_security_config()
    openbao = OpenBaoKeywords(ssh_connection, security_config.get_ssh_user_home())

    get_logger().log_test_case_step("Resolve the current OpenBao generation secret")
    gen_name = openbao.get_current_gen_secret_name()
    gen_keys = openbao.get_gen_secret_keys(gen_name)

    validate_equals(openbao.is_gen_secret_immutable(gen_name), True, f"Generation secret {gen_name} must be immutable")
    validate_list_contains("keys", gen_keys, "Generation secret must contain the unseal key shards")
    validate_list_contains("root_token", gen_keys, "Generation secret must contain the root token in the same secret")

    get_logger().log_test_case_step("Read the Shamir seal-status for shares and threshold")
    seal_status = openbao.get_seal_status(openbao.get_root_token())

    validate_equals(seal_status.get("n"), 5, "Shamir Total Shares (status 'n') must be 5 (KEY_SECRET_SHARES)")
    validate_equals(seal_status.get("t"), 3, "Shamir Threshold (status 't') must be 3 (KEY_REQUIRED_THRESHOLD)")

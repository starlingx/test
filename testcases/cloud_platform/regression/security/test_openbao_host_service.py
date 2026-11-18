"""OpenBao host-service functional tests.

Covers the host-level (package-installed) OpenBao service scenarios that run on
the controller directly, independent of the containerized application:
    - the systemd service is active and enabled on the controller
    - the HCL configuration is valid and carries the expected settings
    - the service self-initializes an admin user, auth methods and kv-v2 engine
    - sensitive config and unseal material is owned by and readable only by the service
    - the host server endpoint serves TLS with a CA-issued, verifiable cert
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
from keywords.bmc.ipmitool.chassis.power.ipmitool_chassis_power_keywords import IPMIToolChassisPowerKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_reboot_keywords import SystemHostRebootKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.cloud_platform.system.openbao.openbao_keywords import OpenBaoKeywords


@mark.p0
def test_host_openbao_service_enabled():
    """Test that the host OpenBao systemd service is active and enabled.

    The host-level OpenBao service is self-managed (active-standby, not Service
    Manager) and is preset-enabled on controllers so it persists across reboot.
    It is expected only on controllers: on DX and Standard both controllers run
    it, while any worker or storage node must not have it enabled. This test is
    topology-aware and runs on SX, DX and Standard.

    Test Steps:
        - connect to the active controller
        - verify the openbao service is active on the active controller
        - verify the openbao service is enabled on every controller
        - verify the openbao service is not enabled on workers or storage nodes
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying the host OpenBao service is active on the active controller")
    validate_equals(openbao.is_host_service_active(), True, "Host OpenBao service must be active on the active controller")

    get_logger().log_test_case_step("Verifying the host OpenBao service is enabled on every controller")
    validate_equals(openbao.is_host_service_enabled_on_all_controllers(), True, "Host OpenBao service must be enabled on all controllers")

    get_logger().log_test_case_step("Verifying the host OpenBao service is not enabled on worker or storage nodes")
    validate_equals(openbao.is_host_service_disabled_on_non_controllers(), True, "Host OpenBao service must not be enabled on non-controller nodes")


@mark.p1
def test_host_openbao_hcl_correctness():
    """Test that the host OpenBao HCL configuration is valid and correct.

    Part A (read-only) of the HCL correctness check: the config passes the
    OpenBao validator and carries the expected raft storage, static auto-unseal
    keyed on the encrypted filesystem, TLS 1.2 listeners, disabled UI and a
    telemetry block. The destructive LuksFS-mount gating (Part B) is out of
    scope here.

    Test Steps:
        - connect to the active controller
        - validate the HCL config with the OpenBao validator
        - read the HCL and verify raft storage, static seal on the encrypted
          filesystem, TLS 1.2 listeners, ui disabled and telemetry present
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Validating the host OpenBao HCL config with the OpenBao validator")
    validate_equals(openbao.validate_host_hcl_config(), True, "Host OpenBao HCL config must validate successfully")

    get_logger().log_test_case_step("Reading the host OpenBao HCL config contents")
    hcl = openbao.get_host_hcl_content()

    get_logger().log_test_case_step("Verifying the HCL carries the expected storage, seal, listener and UI settings")
    validate_str_contains(hcl, 'storage "raft"', "HCL must use raft storage")
    validate_str_contains(hcl, 'seal "static"', "HCL must use static auto-unseal")
    validate_str_contains(hcl, "/var/luks/stx/luks_fs", "Static seal key must reside on the encrypted filesystem")
    validate_str_contains(hcl, "tls_min_version", "HCL listeners must pin a minimum TLS version")
    validate_str_contains(hcl, "ui = false", "HCL must disable the UI")
    validate_str_contains(hcl, "telemetry", "HCL must include a telemetry block")


@mark.p1
def test_host_openbao_self_init():
    """Test that the host OpenBao self-initializes its admin, auth and kv engine.

    At first start the host service initializes itself: it creates an admin
    userpass user (credentials on the encrypted filesystem), enables the
    userpass auth method and a kv-v2 secrets engine, and installs a superuser
    policy. This verifies the platform can authenticate and use the store.

    Test Steps:
        - connect to the active controller
        - log in as admin via userpass using the encrypted-filesystem password
        - verify userpass and token auth methods are present
        - verify the kv-v2 secret engine is mounted at secret/
        - verify the superuser policy exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Logging in to host OpenBao as admin via userpass")
    token = openbao.host_bao_admin_login()
    validate_not_equals(token, "", "Admin userpass login must return a client token")

    get_logger().log_test_case_step("Verifying the userpass and token auth methods are enabled")
    auth_methods = openbao.host_bao_auth_methods(token)
    validate_str_contains(auth_methods, "userpass/", "Host OpenBao must have the userpass auth method")
    validate_str_contains(auth_methods, "token/", "Host OpenBao must have the token auth method")

    get_logger().log_test_case_step("Verifying the kv-v2 secret engine is mounted at secret/")
    secret_mounts = openbao.host_bao_secret_mounts(token)
    validate_str_contains(secret_mounts, "secret/", "Host OpenBao must mount the kv secret engine at secret/")

    get_logger().log_test_case_step("Verifying the superuser policy exists")
    policies = openbao.host_bao_policies(token)
    validate_str_contains(policies, "superuser", "Host OpenBao must install the superuser policy")


@mark.p2
def test_host_openbao_file_permissions():
    """Test that host OpenBao config and unseal material are service-owned only.

    The HCL configuration and the encrypted-filesystem unseal key are owned by
    the openbao service account with owner-only permissions, so a
    non-privileged user (sysadmin) cannot read them.

    Test Steps:
        - connect to the active controller
        - verify the HCL config is owned by openbao:openbao with mode 640
        - verify the unseal key is owned by openbao:openbao with mode 600
        - verify sysadmin cannot read the HCL config
        - verify sysadmin cannot read the unseal key
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Verifying the HCL config is owned by openbao:openbao with mode 640")
    validate_equals(openbao.get_host_file_owner_mode(openbao.HOST_HCL_PATH), "openbao:openbao 640", "HCL config must be owner-only readable by the openbao service")

    get_logger().log_test_case_step("Verifying the unseal key is owned by openbao:openbao with mode 600")
    validate_equals(openbao.get_host_file_owner_mode(openbao.HOST_LUKS_KEY_PATH), "openbao:openbao 600", "Unseal key must be owner-only accessible by the openbao service")

    get_logger().log_test_case_step("Verifying sysadmin cannot read the HCL config")
    validate_equals(openbao.sysadmin_can_read(openbao.HOST_HCL_PATH), False, "sysadmin must not be able to read the HCL config")

    get_logger().log_test_case_step("Verifying sysadmin cannot read the unseal key")
    validate_equals(openbao.sysadmin_can_read(openbao.HOST_LUKS_KEY_PATH), False, "sysadmin must not be able to read the unseal key")


@mark.p1
def test_host_openbao_tls_verify():
    """Test that the host OpenBao server endpoint serves TLS with a CA-issued cert.

    A client trusting the server CA can query the server over TLS and read the
    seal state, and the certificate the server presents verifies against that
    CA and is issued by the platform system-local-ca.

    Test Steps:
        - connect to the active controller
        - query bao status trusting the server CA and confirm the seal state
        - verify the server-presented certificate validates against the CA
        - verify the certificate is issued by the platform CA
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Querying bao status over TLS while trusting the server CA")
    trusted_status = openbao.host_bao_status_with_ca()
    validate_str_contains(trusted_status, "Sealed", "Trusted-CA bao status must report the seal state")
    validate_str_contains(trusted_status, "false", "Host OpenBao server must report Sealed false over trusted TLS")

    get_logger().log_test_case_step("Verifying the server certificate validates against the system CA")
    validate_equals(openbao.host_server_cert_verifies(), True, "Server TLS certificate must verify against the platform system CA")

    get_logger().log_test_case_step("Verifying the server certificate is CA-issued (not self-signed)")
    validate_equals(openbao.is_host_server_cert_ca_issued(), True, "Server certificate must be CA-issued (issuer differs from subject)")


@mark.p0
@mark.lab_has_standby_controller
def test_host_openbao_reboot_auto_unseal(request: FixtureRequest):
    """Host OpenBao auto-unseals from the LuksFS static seal after a graceful reboot.

    Locks, reboots and unlocks the standby controller (the active keeps
    serving), then confirms the standby host service returns active and
    unsealed with the known secret intact, with no manual unseal step.

    Test Steps:
        - Store a known secret via the host bao CLI
        - Lock, reboot and unlock the standby controller
        - Confirm the standby host service is active and reports Sealed false
        - Read the known secret back on the standby
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)
    standby_controller = SystemHostListKeywords(ssh_connection).get_standby_controller().get_host_name()

    get_logger().log_test_case_step("Storing a known secret on the host OpenBao")
    openbao.host_bao_kv_put("reboot-test", {"k": "pre"}, openbao.host_bao_admin_login())

    get_logger().log_test_case_step(f"Locking, rebooting and unlocking the standby {standby_controller}")
    SystemHostLockKeywords(ssh_connection).lock_host(standby_controller)
    SystemHostRebootKeywords(ssh_connection).host_reboot(standby_controller)
    SystemHostLockKeywords(ssh_connection).unlock_host(standby_controller)

    standby_ssh = LabConnectionKeywords().get_ssh_for_hostname(standby_controller)
    standby_openbao = OpenBaoKeywords(standby_ssh)
    validate_equals(standby_openbao.is_host_service_active(), True, "Host OpenBao must be active after reboot")
    validate_str_contains(standby_openbao.host_bao_status_with_ca(), "false", "Host OpenBao must auto-unseal (Sealed false) after reboot")
    validate_str_contains(standby_openbao.host_bao_kv_get("reboot-test", standby_openbao.host_bao_admin_login()), "pre", "Known secret must survive the reboot")


@mark.p1
@mark.lab_has_standby_controller
def test_host_openbao_swact_failover(request: FixtureRequest):
    """Host OpenBao fails over to the new active controller on swact and stays unsealed.

    Steady-state swact failover (happy path): after swacting the active
    controller the host OpenBao service is active and unsealed on the new
    active controller and the known secret is readable.

    Test Steps:
        - Store a known secret on the current active controller
        - Swact the active controller
        - Confirm host OpenBao active and unsealed on the new active controller
        - Read the known secret back on the new active controller
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Storing a known secret before swact")
    openbao.host_bao_kv_put("swact-test", {"k": "pre"}, openbao.host_bao_admin_login())

    get_logger().log_test_case_step("Swacting the active controller")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)
    validate_equals(openbao.is_host_service_active(), True, "Host OpenBao must be active on the new active controller")
    validate_str_contains(openbao.host_bao_status_with_ca(), "false", "Host OpenBao must stay unsealed after swact")
    validate_str_contains(openbao.host_bao_kv_get("swact-test", openbao.host_bao_admin_login()), "pre", "Known secret must survive the swact failover")


@mark.p2
def test_host_openbao_puppet_reapply_no_data_loss(request: FixtureRequest):
    """Host OpenBao survives a puppet runtime re-apply with no data loss.

    Captures the HCL and a known secret, triggers a puppet runtime re-apply,
    and confirms the service re-reads its config without re-seal and the secret
    is intact.

    Test Steps:
        - Confirm the baseline HCL is present and store a known secret
        - Trigger a puppet runtime re-apply of the openbao class
        - Confirm the service stays active and unsealed and the secret is intact
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Recording the HCL and storing a known secret")
    validate_str_contains(openbao.get_host_hcl_content(), "storage", "Baseline HCL must be present before re-apply")
    openbao.host_bao_kv_put("puppet-test", {"k": "pre"}, openbao.host_bao_admin_login())

    get_logger().log_test_case_step("Triggering a puppet runtime re-apply")
    openbao.host_puppet_runtime_reapply()

    validate_equals(openbao.is_host_service_active(), True, "Host OpenBao must stay active after puppet re-apply")
    validate_str_contains(openbao.host_bao_status_with_ca(), "false", "Host OpenBao must stay unsealed after puppet re-apply")
    validate_str_contains(openbao.host_bao_kv_get("puppet-test", openbao.host_bao_admin_login()), "pre", "Known secret must survive the puppet re-apply")


@mark.p2
@mark.lab_has_standby_controller
def test_host_openbao_self_ha_no_self_lock(request: FixtureRequest):
    """Host OpenBao self-HA keeps both controllers as raft peers across swact.

    Validates the self-HA behaviour: both controllers remain raft peers (no
    two-node self-lock), failover on swact keeps the service unsealed, and the
    known secret survives.

    Test Steps:
        - Confirm both controllers appear as raft peers
        - Store a known secret, then swact the active controller
        - Confirm the new active is unsealed, the secret is intact, and both
          controllers remain raft peers
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)

    get_logger().log_test_case_step("Confirming both controllers are raft peers")
    token = openbao.host_bao_admin_login()
    validate_str_contains(openbao.host_raft_list_peers(token), "controller-", "Both controllers must appear as raft peers (no two-node self-lock)")
    openbao.host_bao_kv_put("ha-host", {"k": "hapre"}, token)

    get_logger().log_test_case_step("Swacting the active controller")
    SystemHostSwactKeywords(ssh_connection).host_swact()

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)
    new_token = openbao.host_bao_admin_login()
    validate_str_contains(openbao.host_bao_status_with_ca(), "false", "Host OpenBao must stay unsealed on the new active after swact")
    validate_str_contains(openbao.host_bao_kv_get("ha-host", new_token), "hapre", "Known secret must survive the self-HA failover")
    validate_str_contains(openbao.host_raft_list_peers(new_token), "controller-", "Both controllers must remain raft peers after failover")


@mark.p2
@mark.lab_has_standby_controller
def test_host_openbao_ungraceful_power_loss_auto_unseal(request: FixtureRequest):
    """Host OpenBao auto-unseals after an ungraceful BMC power-cycle.

    Complements the graceful-reboot test: a hard BMC power-cycle (not
    ``system host-reboot``) leaves the LuksFS dirty, yet the host service
    recovers the static seal and auto-unseals with the secret intact. The
    standby controller is power-cycled so the active keeps serving.

    Test Steps:
        - Store a known secret on the host OpenBao
        - Hard BMC power-cycle the standby controller and wait for it to return
        - Confirm the standby host OpenBao is active and unsealed
        - Read the known secret back
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openbao = OpenBaoKeywords(ssh_connection)
    host_list = SystemHostListKeywords(ssh_connection)
    standby_controller = host_list.get_standby_controller().get_host_name()

    get_logger().log_test_case_step(f"Storing a known secret before power-cycling {standby_controller}")
    openbao.host_bao_kv_put("pwrloss", {"k": "pre"}, openbao.host_bao_admin_login())

    get_logger().log_test_case_step(f"Hard BMC power-cycle of {standby_controller}")
    prev_uptime = host_list.get_uptime(standby_controller)
    IPMIToolChassisPowerKeywords(ssh_connection, standby_controller).power_cycle()
    SystemHostRebootKeywords(ssh_connection).wait_for_reboot(standby_controller, prev_uptime)

    standby_ssh = LabConnectionKeywords().get_ssh_for_hostname(standby_controller)
    standby_openbao = OpenBaoKeywords(standby_ssh)
    validate_equals(standby_openbao.is_host_service_active(), True, "Host OpenBao must be active after the ungraceful power-cycle")
    validate_str_contains(standby_openbao.host_bao_status_with_ca(), "false", "Host OpenBao must auto-unseal after the ungraceful power loss")
    validate_str_contains(standby_openbao.host_bao_kv_get("pwrloss", standby_openbao.host_bao_admin_login()), "pre", "Known secret must survive the ungraceful power loss")

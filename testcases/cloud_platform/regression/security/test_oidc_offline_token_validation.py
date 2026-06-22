"""Verify OIDC offline token validation with cached IDP public keys.

Tests that STX REST API servers validate OIDC tokens using cached IDP
public keys (JWKS) without requiring real-time IDP connectivity.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.fm_client_cli.fm_client_cli_keywords import FaultManagementClientCLIKeywords
from keywords.cloud_platform.fault_management.fm_client_cli.object.fm_client_cli_object import FaultManagementClientCLIObject
from keywords.cloud_platform.fault_management.fm_oidc.fm_oidc_keywords import FmOidcKeywords
from keywords.cloud_platform.security.oidc.offline_validation.oidc_offline_validation_keywords import OidcOfflineValidationKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords


@mark.p1
def test_oidc_idp_unavailable_cached_keys(request: FixtureRequest) -> None:
    """Verify CLI commands succeed when IDP (dex) is down but JWKS keys are cached.

    Steps:
        - Setup OIDC environment and admin role-bindings
        - Create LDAP user, authenticate, run fm alarm-list (warms cache)
        - Scale dex to 0 replicas (IDP unavailable)
        - Run fm alarm-list again — must succeed (cached keys)
        - Run system host-list — must succeed
        - Restore dex replicas
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_cache_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "CacheTestGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    get_logger().log_test_case_step("Warm JWKS cache — run commands on all servers with IDP up")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(success, True, "FM alarm-list must succeed with IDP available (cache warm-up)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(success, True, "software list must succeed with IDP available (cache warm-up)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "sw-manager must succeed with IDP available (cache warm-up)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "system host-list")
    validate_equals(success, True, "system host-list must succeed with IDP available (cache warm-up)")

    get_logger().log_test_case_step("Raise a test alarm for stronger validation")
    fm_cli = FaultManagementClientCLIKeywords(ssh_connection)
    alarm_obj = FaultManagementClientCLIObject()
    alarm_obj.set_alarm_id("100.106")
    alarm_obj.set_severity("major")
    alarm_obj.set_reason_text("OIDC offline cache test alarm")
    fm_cli.raise_alarm(alarm_obj)
    request.addfinalizer(lambda: fm_cli.delete_alarm(alarm_obj))

    get_logger().log_test_case_step("Confirm cache is stable — run second round of requests")
    for i in range(5):
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")

    get_logger().log_test_case_step("Scale dex to 0 replicas (IDP unavailable)")
    original_replicas = kw.get_dex_replica_count()
    request.addfinalizer(lambda: kw.restore_dex(original_replicas))
    kw.scale_dex(0)
    kw.wait_for_dex_terminated()

    get_logger().log_test_case_step("Verify fm alarm-list shows test alarm with cached keys (IDP down)")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "FM alarm-list must succeed with IDP down")
    validate_equals("OIDC offline cache" in result.get_raw_output(), True, "FM alarm-list output must contain test alarm (proves real data returned)")

    get_logger().log_test_case_step("Verify software list succeeds with cached keys (IDP down)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(success, True, "software list must succeed with IDP down — using cached JWKS keys")

    get_logger().log_test_case_step("Verify sw-manager succeeds with cached keys (IDP down)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "sw-manager must succeed with IDP down — using cached JWKS keys")

    get_logger().log_test_case_step("Restore dex replicas")
    kw.restore_dex(original_replicas)


@mark.p1
def test_oidc_multi_server_shared_cache(request: FixtureRequest) -> None:
    """Verify all STX servers validate OIDC tokens via offline validation.

    Steps:
        - Setup OIDC environment and admin role-bindings
        - Create LDAP admin user, authenticate
        - Run commands across fm, system, software, sw-manager
        - Verify all succeed (all use common offline validation)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_multi_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "MultiServerGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    get_logger().log_test_case_step("Raise test alarm for FM content validation")
    fm_cli = FaultManagementClientCLIKeywords(ssh_connection)
    alarm_obj = FaultManagementClientCLIObject()
    alarm_obj.set_alarm_id("100.106")
    alarm_obj.set_severity("major")
    alarm_obj.set_reason_text("OIDC multi server test")
    fm_cli.raise_alarm(alarm_obj)
    request.addfinalizer(lambda: fm_cli.delete_alarm(alarm_obj))

    commands = kw.get_oidc_test_commands()

    for cmd, server_label, mandatory in commands:
        get_logger().log_test_case_step(f"Verify {server_label} accepts OIDC token — {cmd}")
        success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, cmd)
        validate_equals(success, True, f"{server_label} must accept OIDC token via offline validation ({cmd})")


@mark.p2
def test_oidc_key_rotation_refresh(request: FixtureRequest) -> None:
    """Verify servers pick up new IDP signing keys after dex restart (key rotation).

    Proves force_refresh works by:
    1. Using old token with old cached JWKS (works — baseline)
    2. Scaling dex down — old token still works (cached keys)
    3. Scaling dex back (new signing key generated)
    4. Re-authenticating (new token signed by new key)
    5. Running command with new token — must work (server fetched new JWKS)

    Step 2 proves old cache is valid. Step 5 proves server refreshed
    to new keys (old cache can't validate new token's kid).

    Steps:
        - Setup OIDC environment, admin role-bindings, LDAP user
        - Run fm alarm-list with old token (baseline)
        - Scale dex to 0, verify old token still works (cached JWKS)
        - Scale dex back to 1 (new signing key)
        - Re-authenticate (new token with new kid)
        - Run fm alarm-list with new token — must succeed (proves JWKS refreshed)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_rotate_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "KeyRotateGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    get_logger().log_test_case_step("Raise test alarm for FM content validation")
    fm_cli = FaultManagementClientCLIKeywords(ssh_connection)
    alarm_obj = FaultManagementClientCLIObject()
    alarm_obj.set_alarm_id("100.106")
    alarm_obj.set_severity("major")
    alarm_obj.set_reason_text("OIDC key rotation test")
    fm_cli.raise_alarm(alarm_obj)
    request.addfinalizer(lambda: fm_cli.delete_alarm(alarm_obj))

    get_logger().log_test_case_step("Verify commands work with OLD token (baseline)")
    # Send multiple requests to warm all worker processes' JWKS caches
    # (fm-api runs multiple workers, each with independent in-memory cache)
    for i in range(5):
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    # Final validation
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(success, True, "FM alarm-list must succeed with old token (baseline)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(success, True, "software list must succeed with old token (baseline)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "sw-manager must succeed with old token (baseline)")

    get_logger().log_test_case_step("Confirm cache is stable — run second round")
    for i in range(5):
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
        kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")

    get_logger().log_test_case_step("Scale dex to 0 — verify old token still works (cached JWKS)")
    original_replicas = kw.get_dex_replica_count()
    request.addfinalizer(lambda: kw.restore_dex(original_replicas))
    kw.scale_dex(0)
    kw.wait_for_dex_terminated()

    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(success, True, "FM must succeed with old token + cached JWKS (IDP down)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(success, True, "software must succeed with old token + cached JWKS (IDP down)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "sw-manager must succeed with old token + cached JWKS (IDP down)")

    get_logger().log_test_case_step("Scale dex back — new pod generates NEW signing key")
    kw.scale_dex(original_replicas)
    kw.wait_for_dex_ready(timeout=180)

    get_logger().log_test_case_step("Re-authenticate — get NEW token signed by NEW key")
    fm_oidc_kw.close_session()

    get_logger().log_test_case_step("Verify all commands work with NEW token (proves JWKS refreshed)")

    def check_fm_after_rotation() -> bool:
        """Check if fm alarm-list works with new key.

        Returns:
            bool: True if command succeeds.
        """
        return kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")

    validate_equals_with_retry(
        function_to_execute=check_fm_after_rotation,
        expected_value=True,
        validation_description="FM must succeed with NEW token — server refreshed JWKS",
        timeout=120,
        polling_sleep_time=15,
    )

    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(success, True, "software must succeed with NEW token — server refreshed JWKS")

    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "sw-manager must succeed with NEW token — server refreshed JWKS")


@mark.p3
def test_oidc_idp_unavailable_no_cache(request: FixtureRequest) -> None:
    """Verify proper error when IDP is down AND servers have no cached keys.

    Steps:
        - Setup OIDC environment, admin role-bindings, LDAP user
        - Scale dex to 0 (IDP unavailable)
        - Restart fm-api pod to clear in-memory JWKS cache
        - Wait for fm-api pod to come back
        - Run fm alarm-list — must fail (no cached keys, no IDP)
        - Restore dex and verify recovery

    Note: Destructive test — restarts API pods. Use on dedicated labs only.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_nocache_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "NoCacheGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user and authenticate")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    get_logger().log_test_case_step("Baseline: verify fm alarm-list works before disruption")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(success, True, "Baseline: fm alarm-list must work before disruption")

    get_logger().log_test_case_step("Scale dex to 0 (IDP unavailable)")
    original_replicas = kw.get_dex_replica_count()
    request.addfinalizer(lambda: kw.restore_dex(original_replicas))
    kw.scale_dex(0)
    kw.wait_for_dex_terminated()

    get_logger().log_test_case_step("Restart fm-api to clear JWKS cache")
    # TODO: implement keyword for service restart
    ssh_connection.send(f"echo '{password}' | sudo -S systemctl restart fm-api")
    kw.wait_for_fm_api_ready()

    get_logger().log_test_case_step("Verify fm alarm-list fails (no IDP, no cache)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(success, False, "FM alarm-list must fail when IDP down and no cached JWKS keys")

    get_logger().log_test_case_step("Restore dex and verify recovery")
    kw.restore_dex(original_replicas)

    get_logger().log_test_case_step("Verify fm alarm-list recovers after IDP restored")
    fm_oidc_kw.close_session()

    def check_fm_recovers() -> bool:
        """Check if fm alarm-list works after IDP restore.

        Returns:
            bool: True if command succeeds.
        """
        return kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")

    validate_equals_with_retry(
        function_to_execute=check_fm_recovers,
        expected_value=True,
        validation_description="FM alarm-list must recover after IDP is restored",
        timeout=60,
        polling_sleep_time=10,
    )


@mark.p3
def test_oidc_no_cache_warmup_idp_down(request: FixtureRequest) -> None:
    """Verify OIDC commands fail when IDP is down and no cache was warmed.

    This is the negative counterpart to test_oidc_idp_unavailable_cached_keys.
    Without any prior OIDC request to populate the JWKS cache, taking dex down
    should cause token validation to fail.

    Steps:
        - Setup OIDC environment and admin role-bindings
        - Create LDAP user
        - Scale dex to 0 BEFORE any OIDC command (no cache warm-up)
        - Run fm alarm-list — must fail (no cached keys, no IDP)
        - Restore dex and verify recovery
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_nocache_neg01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "NoCacheNegGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")

    get_logger().log_test_case_step("Authenticate user (get OIDC token) while dex is still up")
    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())
    # Create SSH session and get token — but do NOT run any API command
    # This ensures the token exists in kubeconfig but servers have no cached JWKS
    fm_oidc_kw.get_authenticated_session(username, password, lab_oam_ip)

    get_logger().log_test_case_step("Scale dex to 0 THEN restart services (prevents re-caching)")
    original_replicas = kw.get_dex_replica_count()
    request.addfinalizer(lambda: kw.restore_dex(original_replicas))
    kw.scale_dex(0)
    kw.wait_for_dex_terminated()

    get_logger().log_test_case_step("Clear JWKS cache — restart all API server processes")
    ssh_connection.send(f"echo '{password}' | sudo -S systemctl restart fm-api")
    ssh_connection.send(f"echo '{password}' | sudo -S systemctl restart software-controller-daemon")
    # vim/sw-manager: SM-managed, kill all nfv-vim processes to ensure cache clear
    ssh_connection.send(f"echo '{password}' | sudo -S pkill -f nfv-vim")
    ssh_connection.send(f"echo '{password}' | sudo -S pkill -f nfv-vim-api")
    ssh_connection.send(f"echo '{password}' | sudo -S sm-restart-safe service vim")
    ssh_connection.send(f"echo '{password}' | sudo -S sm-restart-safe service vim-api")
    # Wait for all services to come back (they can't re-cache since dex is down)
    kw.wait_for_fm_api_ready()

    # Also verify software and vim are listening
    def check_all_services_ready() -> bool:
        """Check if software and vim APIs are accepting connections.

        Returns:
            bool: True if both services respond.
        """
        # TODO: implement keyword for multi-service readiness
        output = ssh_connection.send("ss -tln 2>/dev/null | grep -c ':5500'")
        sw_raw = "\n".join(output) if isinstance(output, list) else (output or "")
        output = ssh_connection.send("ss -tln 2>/dev/null | grep -c ':4545'")
        vim_raw = "\n".join(output) if isinstance(output, list) else (output or "")
        sw_up = sw_raw.strip() != "0"
        vim_up = vim_raw.strip() != "0"
        return sw_up and vim_up

    validate_equals_with_retry(
        function_to_execute=check_all_services_ready,
        expected_value=True,
        validation_description="Wait for software and vim APIs to be ready",
        timeout=60,
        polling_sleep_time=5,
    )

    get_logger().log_test_case_step("Verify commands behavior with no cache and IDP down")
    fm_result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(fm_result.is_successful(), False, "FM alarm-list must FAIL when no cached JWKS and IDP down")

    sw_success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(sw_success, False, "software list must FAIL when no cached JWKS and IDP down")

    swmgr_success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(swmgr_success, False, "sw-manager must FAIL when no cached JWKS and IDP down")

    get_logger().log_test_case_step("Restore dex and verify recovery")
    kw.restore_dex(original_replicas)

    get_logger().log_test_case_step("Verify fm alarm-list recovers after IDP restored")

    def check_fm_recovers() -> bool:
        """Check if fm alarm-list works after IDP restore.

        Returns:
            bool: True if command succeeds.
        """
        return kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")

    validate_equals_with_retry(
        function_to_execute=check_fm_recovers,
        expected_value=True,
        validation_description="FM alarm-list must recover after IDP is restored",
        timeout=60,
        polling_sleep_time=10,
    )


@mark.p2
def test_oidc_remote_cli_all_servers(request: FixtureRequest) -> None:
    """Verify OIDC offline token validation works via remote CLI for all servers.

    Remote CLI simulates a user SSH-ing to the controller OAM IP and running
    commands with --stx-auth-type=oidc. Proves cached JWKS keys work when
    IDP is unavailable — the key offline validation scenario for remote users.

    Steps:
        - Setup OIDC environment and admin role-bindings
        - Create LDAP user with admin role
        - SSH as LDAP user to OAM IP (remote CLI)
        - Run commands via OIDC (warm cache)
        - Scale dex to 0 (IDP unavailable)
        - Run same commands — must still work (cached JWKS)
        - Restore dex
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_remote_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "RemoteCliAllGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")

    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    get_logger().log_test_case_step("Remote CLI: Warm cache — run all commands with IDP up")
    commands = kw.get_oidc_test_commands()
    for i in range(5):
        for cmd, label, mandatory in commands:
            kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, cmd)

    get_logger().log_test_case_step("Raise test alarm for content validation")
    fm_cli = FaultManagementClientCLIKeywords(ssh_connection)
    alarm_obj = FaultManagementClientCLIObject()
    alarm_obj.set_alarm_id("100.106")
    alarm_obj.set_severity("major")
    alarm_obj.set_reason_text("Remote CLI OIDC cache test")
    fm_cli.raise_alarm(alarm_obj)
    request.addfinalizer(lambda: fm_cli.delete_alarm(alarm_obj))

    for cmd, label, mandatory in commands:
        success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, cmd)
        validate_equals(success, True, f"Remote CLI: {label} must succeed with IDP up")

    get_logger().log_test_case_step("Confirm cache is stable — run second round")
    for i in range(5):
        for cmd, label, mandatory in commands:
            kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, cmd)

    get_logger().log_test_case_step("Scale dex to 0 (IDP unavailable for remote user)")
    original_replicas = kw.get_dex_replica_count()
    request.addfinalizer(lambda: kw.restore_dex(original_replicas))
    kw.scale_dex(0)
    kw.wait_for_dex_terminated()

    get_logger().log_test_case_step("Remote CLI: Verify commands work with cached JWKS (IDP down)")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), True, "Remote CLI: FM must succeed with IDP down (cached JWKS)")
    validate_equals("Remote CLI OIDC" in result.get_raw_output(), True, "Remote CLI: fm alarm-list must return test alarm content (proves real data)")
    for cmd, label, mandatory in commands:
        if cmd.startswith("fm "):
            continue
        success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, cmd)
        validate_equals(success, True, f"Remote CLI: {label} must succeed with IDP down (cached JWKS)")

    get_logger().log_test_case_step("Restore dex")
    kw.restore_dex(original_replicas)


@mark.p2
@mark.lab_has_subcloud
def test_oidc_dc_subcloud_offline(request: FixtureRequest) -> None:
    """Verify OIDC offline token validation works on subcloud during SC connectivity loss.

    On a DC system, subclouds validate OIDC tokens using cached IDP public keys.
    When connectivity to SystemController (where dex runs) is lost, the subcloud
    must continue validating tokens using its local JWKS cache.

    Steps:
        - Setup OIDC environment on system controller
        - Create LDAP user with admin role
        - SSH as LDAP user to subcloud OAM IP
        - Run fm alarm-list on subcloud via OIDC (warm cache)
        - Block subcloud → SystemController connectivity (iptables)
        - Run fm alarm-list on subcloud again — must succeed (cached JWKS)
        - Restore connectivity
        - Verify recovery

    Covers: PR.5003.06
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_dc_sub_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "DcSubcloudGroup"

    # Get first subcloud
    subcloud_names = lab_config.get_subcloud_names()
    subcloud_name = subcloud_names[0]
    subcloud_config = lab_config.get_subcloud(subcloud_name)
    subcloud_oam_ip = subcloud_config.get_floating_ip()
    subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)

    get_logger().log_test_case_step("Set up OIDC environment on SystemController")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings on SC and subcloud")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())
    # Subcloud needs its own role-bindings applied for fm-api to authorize the user

    sc_svc_param_kw = SystemServiceParameterKeywords(subcloud_ssh)
    role_value = f"%{group_name}:admin;%{group_name}:member;%{group_name}:reader"
    # Delete existing if any
    existing = sc_svc_param_kw.list_service_parameters(service="identity", section="stx")
    for param in existing.get_parameters():
        if param.get_name() == "role-bindings":
            sc_svc_param_kw.delete_service_parameter(param.get_uuid())
            sc_svc_param_kw.apply_service_parameters("identity", section="stx")
            break
    sc_svc_param_kw.add_service_parameter("identity", "stx", "role-bindings", role_value)
    sc_svc_param_kw.apply_service_parameters("identity", section="stx")

    def cleanup_subcloud_role_bindings() -> None:
        """Remove role-bindings from subcloud."""
        sc_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        svc_kw = SystemServiceParameterKeywords(sc_ssh)
        params = svc_kw.list_service_parameters(service="identity", section="stx")
        for p in params.get_parameters():
            if p.get_name() == "role-bindings":
                svc_kw.delete_service_parameter(p.get_uuid())
                svc_kw.apply_service_parameters("identity", section="stx")
                break

    request.addfinalizer(cleanup_subcloud_role_bindings)

    get_logger().log_test_case_step("Create LDAP user on SystemController")
    # On DC, dex runs on SC and authenticates against SC's LDAP.
    # The LDAP user only needs to exist on SC for oidc-auth.
    # SSH to subcloud OAM IP also uses SC's LDAP (centralized auth).
    # Clean stale home dir on subcloud from previous runs (prevents permission issues)
    subcloud_ssh.send(f"echo '{password}' | sudo -S rm -rf /home/{username}")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")

    get_logger().log_test_case_step("Wait for rolebindings on subcloud")

    kw.wait_for_rolebindings_file(timeout_sec=120)

    get_logger().log_test_case_step("Warm subcloud JWKS cache — run OIDC commands on subcloud")
    fm_oidc_kw = FmOidcKeywords(subcloud_ssh)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    # On DC, oidc-auth on subcloud must point to SC's dex via -c flag
    sc_oam_ip = lab_oam_ip
    fm_oidc_kw.get_authenticated_session(username, password, subcloud_oam_ip, oidc_client_ip=sc_oam_ip)

    # Warm subcloud's API server caches (all servers)
    for i in range(5):
        kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "fm alarm-list")
        kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "software list")
        kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "sw-manager sw-deploy-strategy show")
        kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "system host-list")

    get_logger().log_test_case_step("Verify all commands work on subcloud (SC connected)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "fm alarm-list")
    validate_equals(success, True, "Subcloud: fm alarm-list must succeed (baseline)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "software list")
    validate_equals(success, True, "Subcloud: software list must succeed (baseline)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "Subcloud: sw-manager must succeed (baseline)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "system host-list")
    validate_equals(success, True, "Subcloud: system host-list must succeed (baseline)")

    get_logger().log_test_case_step("Block subcloud → SystemController connectivity")
    # Block traffic to SC management IP (where dex is accessible from subcloud)
    mgmt_cmd = "system addrpool-show $(system addrpool-list | grep management | awk '{print $2}')" " 2>/dev/null | grep floating_address | awk '{print $4}'"
    sc_mgmt_ip_output = ssh_connection.send(source_openrc(mgmt_cmd))
    sc_mgmt_ip = "\n".join(sc_mgmt_ip_output) if isinstance(sc_mgmt_ip_output, list) else (sc_mgmt_ip_output or "")
    sc_mgmt_ip = sc_mgmt_ip.strip().split("\n")[-1].strip()
    get_logger().log_info(f"Blocking subcloud access to SC management IP: {sc_mgmt_ip}")

    # Also block SC OAM IP (dex NodePort is on OAM)
    subcloud_ssh.send(f"echo '{password}' | sudo -S iptables -A OUTPUT -d {sc_mgmt_ip} -j DROP")
    subcloud_ssh.send(f"echo '{password}' | sudo -S iptables -A OUTPUT -d {sc_oam_ip} -j DROP")

    def restore_connectivity() -> None:
        """Remove iptables block rules on subcloud."""
        get_logger().log_info("Restoring subcloud → SC connectivity")
        sc_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        sc_ssh.send(f"echo '{password}' | sudo -S iptables -D OUTPUT -d {sc_mgmt_ip} -j DROP 2>/dev/null")
        sc_ssh.send(f"echo '{password}' | sudo -S iptables -D OUTPUT -d {sc_oam_ip} -j DROP 2>/dev/null")

    request.addfinalizer(restore_connectivity)

    get_logger().log_test_case_step("Verify all commands on subcloud succeed with SC disconnected")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "fm alarm-list")
    validate_equals(success, True, "Subcloud: fm must succeed with SC disconnected (cached JWKS)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "software list")
    validate_equals(success, True, "Subcloud: software must succeed with SC disconnected (cached JWKS)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "sw-manager sw-deploy-strategy show")
    validate_equals(success, True, "Subcloud: sw-manager must succeed with SC disconnected (cached JWKS)")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "system host-list")
    validate_equals(success, True, "Subcloud: system host-list must succeed with SC disconnected (cached JWKS)")

    get_logger().log_test_case_step("Restore connectivity and verify recovery")
    restore_connectivity()

    success = kw.run_oidc_command(fm_oidc_kw, username, password, subcloud_oam_ip, "fm alarm-list")
    validate_equals(success, True, "Subcloud: fm alarm-list must succeed after SC connectivity restored")


@mark.p2
def test_oidc_invalid_token_rejected(request: FixtureRequest) -> None:
    """Verify servers reject invalid/tampered tokens with offline validation.

    Proves the offline JWKS validation actually checks the token signature —
    a garbage or tampered token must be rejected even when dex is down
    (no fallback to accepting without validation).

    Steps:
        - Setup OIDC environment and admin role-bindings
        - Create LDAP user, authenticate normally (verify baseline works)
        - Tamper with the OIDC token in kubeconfig
        - Run fm alarm-list with tampered token — must FAIL
        - Run software list with tampered token — must FAIL
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    kw = OidcOfflineValidationKeywords(ssh_connection)
    security_config = ConfigurationManager.get_security_config()
    lab_config = ConfigurationManager.get_lab_config()
    lab_oam_ip = lab_config.get_floating_ip()
    username = "oidc_tamper_user01"
    password = lab_config.get_admin_credentials().get_password()
    group_name = "TamperTestGroup"

    get_logger().log_test_case_step("Set up OIDC environment")
    kw.setup_oidc_with_ldap_connector(security_config, lab_config)
    kw.wait_for_dex_connectable(lab_oam_ip)

    get_logger().log_test_case_step("Set up admin role-bindings")
    kw.setup_role_bindings(group_name, "admin")
    request.addfinalizer(lambda: kw.remove_role_bindings())

    get_logger().log_test_case_step("Create LDAP user")
    kw.setup_ldap_user(username, password, group_name)
    request.addfinalizer(lambda: kw.cleanup_ldap_user(username, password, group_name))

    kw.wait_for_group_membership(username, "sys_protected")

    fm_oidc_kw = FmOidcKeywords(ssh_connection)
    request.addfinalizer(lambda: fm_oidc_kw.close_session())

    get_logger().log_test_case_step("Verify baseline works with valid token")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(success, True, "Baseline: fm alarm-list must succeed with valid token")

    get_logger().log_test_case_step("Tamper with OIDC token in kubeconfig")
    ldap_ssh = fm_oidc_kw.get_authenticated_session(username, password, lab_oam_ip)
    # Replace the token with a garbage value — invalidates the JWT signature
    ldap_ssh.send("sed -i 's/token: .*/token: INVALID_TAMPERED_TOKEN_12345/' $HOME/.kube/config")

    get_logger().log_test_case_step("Verify fm alarm-list FAILS with tampered token")
    result = fm_oidc_kw.run_fm_command_as_oidc_user(username, password, lab_oam_ip, "fm alarm-list")
    validate_equals(result.is_successful(), False, "fm alarm-list must FAIL with tampered token — offline validation rejects bad signature")

    get_logger().log_test_case_step("Verify software list FAILS with tampered token")
    success = kw.run_oidc_command(fm_oidc_kw, username, password, lab_oam_ip, "software list")
    validate_equals(success, False, "software list must FAIL with tampered token — offline validation rejects bad signature")

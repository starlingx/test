"""Verify oidc-auth-apps supports overriding the dex telemetry nodePort.

On affected releases the oidc-dex service exposed http, telemetry and https
nodePorts, but only the http nodePort honoured a helm override. The telemetry
nodePort stayed randomly assigned, which could collide with a statically
configured nodePort and cause a deploy failure. All three nodePorts must be
overridable.

The dex chart rejects a partial override: a dex helm override must be
self-complete (connectors, volumeMounts for /etc/dex/tls, volumes). This test
therefore establishes a complete, valid dex configuration via the shared OIDC
setup keyword, then applies a self-complete dex override that carries the same
configuration plus a service.ports block pinning the http, telemetry and https
nodePorts. After re-applying oidc-auth-apps it asserts each named port on the
oidc-dex service took the configured value; the telemetry assertion is the
regression check, since previously it stayed randomly assigned.

Lab preconditions, which this test does not create:
    - oidc-auth-apps installed on the system.
    - Local LDAP available for the dex connector.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.cloud_platform.security.oidc.oidc_setup_keywords import DEX_LOCAL_LDAP_OVERRIDE, OIDC_APP_NAME, OIDC_NAMESPACE, OidcSetupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.addrpool.system_addrpool_list_keywords import SystemAddrpoolListKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.service.kubectl_get_service_keywords import KubectlGetServiceKeywords
from keywords.linux.keyring.keyring_keywords import KeyringKeywords

OIDC_DEX_SERVICE = "oidc-dex"
DEX_CHART = "dex"
DEX_OVERRIDE_FILE = "/tmp/dex-nodeport-override.yaml"
# Non-default nodePorts inside the Kubernetes NodePort range (30000-32767), away
# from the platform defaults (30555/30556) so a stale value is detectable.
OVERRIDE_HTTP_NODEPORT = "31666"
OVERRIDE_TELEMETRY_NODEPORT = "31667"
OVERRIDE_HTTPS_NODEPORT = "31668"
# service.ports block appended to the complete dex override so the override stays
# self-complete (the dex chart rejects a ports-only override).
DEX_NODEPORT_BLOCK = """service:
  type: NodePort
  ports:
    http:
      nodePort: {http_port}
    telemetry:
      nodePort: {telemetry_port}
    https:
      nodePort: {https_port}
"""
APPLY_TIMEOUT = 900
APPLY_POLL_INTERVAL = 15


@mark.p2
def test_oidc_dex_telemetry_nodeport_override(request: FixtureRequest):
    """Verify the dex telemetry nodePort honours a helm override.

    Test Steps:
        - Establish a complete, valid dex configuration via the OIDC setup keyword
        - Build a self-complete dex override adding http, telemetry and https nodePorts
        - Apply the override and re-apply oidc-auth-apps
        - Verify the http nodePort took the configured value
        - Verify the telemetry nodePort took the configured value
        - Verify the https nodePort took the configured value
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    oidc_setup = OidcSetupKeywords(ssh_connection)
    service_keywords = KubectlGetServiceKeywords(ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    apply_keywords = SystemApplicationApplyKeywords(ssh_connection)

    request.addfinalizer(oidc_setup.cleanup_oidc_environment)

    get_logger().log_setup_step("Establish a complete valid dex configuration")
    oidc_setup.setup_oidc_environment()

    get_logger().log_test_case_step("Build a self-complete dex override adding the nodePorts")
    ldap_admin_pw = KeyringKeywords(ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
    mgmt_ip = SystemAddrpoolListKeywords(ssh_connection).get_system_addrpool_list().get_management_floating_address()
    if ":" in mgmt_ip:
        mgmt_ip = f"[{mgmt_ip}]"
    dex_override = DEX_LOCAL_LDAP_OVERRIDE.format(ldap_admin_pw=ldap_admin_pw, mgmt_ip=mgmt_ip)
    nodeport_block = DEX_NODEPORT_BLOCK.format(http_port=OVERRIDE_HTTP_NODEPORT, telemetry_port=OVERRIDE_TELEMETRY_NODEPORT, https_port=OVERRIDE_HTTPS_NODEPORT)
    file_keywords.create_file_with_heredoc(DEX_OVERRIDE_FILE, f"{dex_override}{nodeport_block}")

    def restore_dex_config():
        get_logger().log_teardown_step("Restoring dex configuration without nodePort overrides")
        restore_ssh = LabConnectionKeywords().get_active_controller_ssh()
        OidcSetupKeywords(restore_ssh).setup_oidc_environment()

    request.addfinalizer(restore_dex_config)

    get_logger().log_test_case_step("Apply the dex override and re-apply oidc-auth-apps")
    helm_override_keywords.update_helm_override(DEX_OVERRIDE_FILE, OIDC_APP_NAME, DEX_CHART, OIDC_NAMESPACE)
    apply_keywords.system_application_apply(OIDC_APP_NAME, timeout=APPLY_TIMEOUT, wait_for_applied=True)

    get_logger().log_test_case_step("Verify http nodePort took the configured value")
    validate_equals_with_retry(
        lambda: service_keywords.get_service_node_port_by_name(OIDC_DEX_SERVICE, "http", OIDC_NAMESPACE),
        OVERRIDE_HTTP_NODEPORT,
        "dex http nodePort should match the configured override",
        timeout=APPLY_TIMEOUT,
        polling_sleep_time=APPLY_POLL_INTERVAL,
    )

    get_logger().log_test_case_step("Verify telemetry nodePort took the configured value")
    telemetry_nodeport = service_keywords.get_service_node_port_by_name(OIDC_DEX_SERVICE, "telemetry", OIDC_NAMESPACE)
    validate_equals(telemetry_nodeport, OVERRIDE_TELEMETRY_NODEPORT, "dex telemetry nodePort should match the configured override")

    get_logger().log_test_case_step("Verify https nodePort took the configured value")
    https_nodeport = service_keywords.get_service_node_port_by_name(OIDC_DEX_SERVICE, "https", OIDC_NAMESPACE)
    validate_equals(https_nodeport, OVERRIDE_HTTPS_NODEPORT, "dex https nodePort should match the configured override")

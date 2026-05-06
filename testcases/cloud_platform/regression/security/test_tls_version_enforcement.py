"""Tests for TLS version enforcement on all externally visible platform HTTPS endpoints.

Validates that minimum TLS version configuration is enforced across HAProxy,
Docker Registry, OpenLDAP, and Kubernetes API endpoints. Covers both platform
and kubernetes service parameter paths.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.tls_keywords import TlsKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.service.system_service_parameter_keywords import SystemServiceParameterKeywords

# All externally visible platform HTTPS endpoints
ENDPOINTS = [
    {"port": 8443, "name": "StarlingX Horizon", "use_oam": True},
    {"port": 443, "name": "OAM HTTPS (Ingress)", "use_oam": True},
    {"port": 6443, "name": "Kubernetes API (HAProxy)", "use_oam": True},
    {"port": 9001, "name": "Docker Registry", "host": "registry.local"},
    {"port": 636, "name": "OpenLDAP", "use_mgmt": True},
    {"port": 30556, "name": "OIDC DEX", "use_oam": True},
]

# Endpoints controlled by 'platform config' service parameters
PLATFORM_ENDPOINTS = [
    {"port": 9001, "name": "Docker Registry", "host": "registry.local"},
    {"port": 636, "name": "OpenLDAP", "use_mgmt": True},
    {"port": 30556, "name": "OIDC DEX", "use_oam": True},
]

# Endpoints controlled by 'kubernetes kube_apiserver' service parameters
K8S_ENDPOINTS = [
    {"port": 16443, "name": "Kubernetes API (kube_apiserver)", "use_oam": True},
]

# HAProxy-fronted platform endpoints where HAProxy terminates SSL
HAPROXY_ENDPOINTS = [
    {"port": 5000, "name": "Keystone", "use_oam": True},
    {"port": 6385, "name": "System Inventory REST API", "use_oam": True},
    {"port": 6443, "name": "Kubernetes API (k8s-frontend)", "use_oam": True},
    {"port": 7777, "name": "Service Manager API", "use_oam": True},
    {"port": 9311, "name": "Barbican", "use_oam": True},
    {"port": 15497, "name": "USM", "use_oam": True},
    {"port": 18002, "name": "Fault Management API", "use_oam": True},
    {"port": 4545, "name": "VIM", "use_oam": True},
    {"port": 8443, "name": "StarlingX Horizon", "use_oam": True},
    {"port": 443, "name": "OAM HTTPS (Ingress)", "use_oam": True},
]


@mark.p0
def test_tls11_connections_rejected(request):
    """Verify TLS 1.1 connections are rejected when default minimum is TLS 1.2.

    Test Steps:
        - Connect with -tls1_1 to each endpoint and verify handshake failure
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    for ep in ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        get_logger().log_test_case_step(f"Verifying TLS 1.1 rejected on {ep['name']}")
        tls_kw.verify_tls_rejected(host, ep["port"], "-tls1_1", ep["name"], ep_is_ipv6)


@mark.p0
def test_tls12_connections_accepted(request):
    """Verify TLS 1.2 connections are accepted when minimum is TLS 1.2.

    Test Steps:
        - Connect with -tls1_2 to each endpoint and verify handshake succeeds
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    for ep in ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        get_logger().log_test_case_step(f"Verifying TLS 1.2 accepted on {ep['name']}")
        tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)


@mark.p0
def test_tls13_connections_accepted(request):
    """Verify TLS 1.3 connections are accepted on all endpoints.

    Test Steps:
        - Connect with -tls1_3 to each endpoint and verify handshake succeeds
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    for ep in ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        get_logger().log_test_case_step(f"Verifying TLS 1.3 accepted on {ep['name']}")
        tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_3", ep["name"], ep_is_ipv6)


@mark.p0
def test_set_min_tls13_platform_endpoints(request):
    """Verify platform endpoints reject TLS 1.2 when minimum is set to TLS 1.3.

    Tests platform-controlled endpoints (Docker Registry:9001, OpenLDAP:636).
    HAProxy uses ssl-default-bind-options to enforce TLS minimum.

    Note: OpenLDAP on Bullseye (slapd 2.4/GnuTLS) doesn't properly enforce
    olcTLSProtocolMin:3.4 - TLS 1.2 connections still work. This is expected.

    Test Steps:
        - Set platform tls-min-version to VersionTLS13
        - Apply platform service parameters
        - Verify TLS 1.2 rejected and TLS 1.3 accepted on platform endpoints
        - Verify haproxy.cfg contains no-tlsv12
    Teardown:
        - Revert tls-min-version to VersionTLS12
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceParameterKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    tls_kw = TlsKeywords(ssh_connection)
    ep_ips = tls_kw.get_endpoint_ips()
    os_version = tls_kw.get_os_version()

    def teardown():
        """Revert platform tls-min-version to VersionTLS12."""
        get_logger().log_teardown_step("Reverting tls-min-version to VersionTLS12")
        service_keywords.modify_service_parameter("platform", "config", "tls-min-version", "VersionTLS12")
        service_keywords.apply_service_parameters("platform")

    request.addfinalizer(teardown)

    # Step 1-2: Set TLS 1.3 minimum and apply
    get_logger().log_test_case_step("Setting platform tls-min-version to VersionTLS13")
    service_keywords.modify_service_parameter("platform", "config", "tls-min-version", "VersionTLS13")
    service_keywords.apply_service_parameters("platform")
    tls_kw.wait_for_config_out_of_date_alarm_clear()

    # Step 3-4: For each platform endpoint, verify TLS 1.2 rejected then TLS 1.3 accepted
    for ep in PLATFORM_ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")

        # OpenLDAP on Bullseye: slapd 2.4/GnuTLS doesn't enforce TLS 1.3 minimum - TLS 1.2 still accepted
        if ep["name"] == "OpenLDAP" and os_version == "bullseye":
            get_logger().log_info(f"OpenLDAP on {os_version}: validating TLS 1.2 IS accepted (known limitation)")
            tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)
        # OIDC DEX: Go binary on direct NodePort, not controlled by platform tls-min-version
        elif ep["name"] == "OIDC DEX" and os_version in ("bullseye", "trixie"):
            get_logger().log_info("OIDC DEX: validating TLS 1.2 IS accepted (known limitation - not fronted by HAProxy)")
            tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)
        else:
            tls_kw.verify_tls_rejected(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)

        tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_3", ep["name"], ep_is_ipv6)

    # Step 5: Verify haproxy config
    get_logger().log_info("Verifying haproxy ssl-default-bind-options contains no-tlsv12")
    haproxy_opts = tls_kw.get_haproxy_bind_options()
    validate_equals(
        "no-tlsv12" in haproxy_opts,
        True,
        "haproxy.cfg ssl-default-bind-options contains no-tlsv12",
    )


@mark.p0
def test_set_min_tls13_k8s_endpoints(request):
    """Verify K8s endpoints reject TLS 1.2 when minimum is set to TLS 1.3.

    Tests K8s-controlled endpoints (Kubernetes API:16443).
    Controlled by 'kubernetes kube_apiserver tls-min-version'.

    Test Steps:
        - Set kubernetes kube_apiserver tls-min-version to VersionTLS13
        - Apply kubernetes service parameters
        - Verify TLS 1.2 rejected and TLS 1.3 accepted on K8s endpoints
    Teardown:
        - Revert kubernetes tls-min-version to VersionTLS12
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceParameterKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    tls_kw = TlsKeywords(ssh_connection)
    ep_ips = tls_kw.get_endpoint_ips()

    def teardown():
        """Revert kubernetes kube_apiserver tls-min-version to VersionTLS12."""
        get_logger().log_teardown_step("Reverting kubernetes kube_apiserver tls-min-version to VersionTLS12")
        service_keywords.modify_service_parameter("kubernetes", "kube_apiserver", "tls-min-version", "VersionTLS12")
        service_keywords.apply_service_parameters("kubernetes")

    request.addfinalizer(teardown)

    # Step 1-2: Set K8s TLS 1.3 minimum and apply (waits for K8s restart)
    get_logger().log_test_case_step("Setting kubernetes kube_apiserver tls-min-version to VersionTLS13")
    service_keywords.modify_service_parameter("kubernetes", "kube_apiserver", "tls-min-version", "VersionTLS13")
    service_keywords.apply_service_parameters("kubernetes")
    tls_kw.wait_for_config_out_of_date_alarm_clear()

    # Step 3-4: For each K8s endpoint, verify TLS 1.2 rejected then TLS 1.3 accepted
    for ep in K8S_ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        tls_kw.verify_tls_rejected(host, ep["port"], "-tls1_2", ep["name"], ep_ips.is_ipv6_lab())
        tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_3", ep["name"], ep_ips.is_ipv6_lab())


@mark.p0
def test_haproxy_tls11_not_accepted(request):
    """Verify HAProxy rejects TLS 1.1 on platform ports (default min = TLS 1.2).

    Checks that haproxy.cfg contains no-tlsv10 and no-tlsv11 flags, and that
    TLS 1.1 connections are rejected on HAProxy-fronted ports.

    Test Steps:
        - Verify haproxy.cfg contains no-tlsv10 and no-tlsv11
        - Connect with -tls1_1 to each HAProxy port and verify rejection
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    tls_kw = TlsKeywords(ssh_connection)
    ep_ips = tls_kw.get_endpoint_ips()

    # Verify haproxy config has no-tlsv10 and no-tlsv11
    get_logger().log_test_case_step("Verifying haproxy.cfg contains no-tlsv10 and no-tlsv11")
    haproxy_opts = tls_kw.get_haproxy_bind_options()
    validate_equals("no-tlsv10" in haproxy_opts, True, "haproxy.cfg contains no-tlsv10")
    validate_equals("no-tlsv11" in haproxy_opts, True, "haproxy.cfg contains no-tlsv11")

    # Verify TLS 1.1 connections are rejected on HAProxy-fronted ports
    for ep in HAPROXY_ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        tls_kw.verify_tls_rejected(host, ep["port"], "-tls1_1", ep["name"], ep_is_ipv6)


@mark.p0
def test_haproxy_tls12_allowed(request):
    """Verify HAProxy allows TLS 1.2 on platform ports (default min = TLS 1.2).

    Checks that haproxy.cfg does NOT contain no-tlsv12 (TLS 1.2 is permitted),
    and that TLS 1.2 connections succeed on HAProxy-fronted ports.

    Test Steps:
        - Verify haproxy.cfg does NOT contain no-tlsv12
        - Connect with -tls1_2 to each HAProxy port and verify success
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    tls_kw = TlsKeywords(ssh_connection)
    ep_ips = tls_kw.get_endpoint_ips()

    # Verify haproxy config does NOT have no-tlsv12 (TLS 1.2 should be allowed)
    get_logger().log_test_case_step("Verifying haproxy.cfg does NOT contain no-tlsv12")
    haproxy_opts = tls_kw.get_haproxy_bind_options()
    validate_equals("no-tlsv12" in haproxy_opts, False, "haproxy.cfg does NOT contain no-tlsv12 (TLS 1.2 allowed)")

    # Verify TLS 1.2 connections are accepted on HAProxy-fronted ports
    for ep in HAPROXY_ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)


@mark.p0
def test_haproxy_no_tls10_tls11_tls12_when_min_tls13(request):
    """Verify HAProxy blocks TLS 1.0/1.1/1.2 when platform min is set to TLS 1.3.

    Sets platform min to TLS 1.3, then verifies haproxy.cfg ssl-default-bind-options
    contains no-sslv3, no-tlsv10, no-tlsv11, no-tlsv12 and that TLS 1.1/1.2 are
    rejected while TLS 1.3 is accepted on HAProxy-fronted ports.

    Test Steps:
        - Set platform tls-min-version to VersionTLS13
        - Verify haproxy.cfg contains all no-tls flags
        - Verify TLS 1.1 and 1.2 rejected, TLS 1.3 accepted on HAProxy ports
    Teardown:
        - Revert tls-min-version to VersionTLS12
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceParameterKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    tls_kw = TlsKeywords(ssh_connection)
    ep_ips = tls_kw.get_endpoint_ips()
    os_version = tls_kw.get_os_version()

    def teardown():
        """Revert platform tls-min-version to VersionTLS12."""
        get_logger().log_teardown_step("Reverting tls-min-version to VersionTLS12")
        service_keywords.modify_service_parameter("platform", "config", "tls-min-version", "VersionTLS12")
        service_keywords.apply_service_parameters("platform")

    request.addfinalizer(teardown)

    # Set TLS 1.3 minimum and apply
    get_logger().log_test_case_step("Setting platform tls-min-version to VersionTLS13")
    service_keywords.modify_service_parameter("platform", "config", "tls-min-version", "VersionTLS13")
    service_keywords.apply_service_parameters("platform")
    tls_kw.wait_for_config_out_of_date_alarm_clear()

    # Verify haproxy config has all the no-tls flags
    haproxy_opts = tls_kw.get_haproxy_bind_options()
    for flag in ["no-sslv3", "no-tlsv10", "no-tlsv11", "no-tlsv12"]:
        validate_equals(flag in haproxy_opts, True, f"haproxy.cfg contains {flag}")

    # Verify TLS 1.1 and 1.2 rejected, TLS 1.3 accepted on HAProxy-fronted ports
    for ep in HAPROXY_ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        tls_kw.verify_tls_rejected(host, ep["port"], "-tls1_1", ep["name"], ep_is_ipv6)

        # Horizon on Bullseye: lighttpd 1.4.55 lacks ssl.openssl.ssl-conf-cmd;
        # OpenSSL 1.1.1 always permits TLS 1.2 - validate it IS accepted
        if ep["port"] == 8443 and os_version == "bullseye":
            get_logger().log_info(f"Horizon on {os_version}: validating TLS 1.2 IS accepted (lighttpd limitation)")
            tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)
        else:
            tls_kw.verify_tls_rejected(host, ep["port"], "-tls1_2", ep["name"], ep_is_ipv6)

        tls_kw.verify_tls_accepted(host, ep["port"], "-tls1_3", ep["name"], ep_is_ipv6)

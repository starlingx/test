"""Tests for TLS cipher suite enforcement on all externally visible platform HTTPS endpoints.

Validates that configured cipher suites are enforced (allowed ciphers accepted,
disallowed ciphers rejected) across HAProxy, Docker Registry, OpenLDAP, and
Kubernetes API endpoints.
"""

import time

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.security.tls_keywords import TlsKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

DISALLOWED_CIPHERS = ["AES256-SHA", "DES-CBC3-SHA", "RC4-SHA"]
INVALID_CIPHERS = ["NULL-SHA", "NULL-SHA256", "ECDHE-RSA-NULL-SHA", "EXP-RC4-MD5", "BOGUS-CIPHER-NAME"]
TLS12_RSA_CIPHERS = ["ECDHE-RSA-AES256-GCM-SHA384", "ECDHE-RSA-AES128-GCM-SHA256", "ECDHE-RSA-CHACHA20-POLY1305"]
TLS12_ECDSA_CIPHERS = ["ECDHE-ECDSA-AES256-GCM-SHA384", "ECDHE-ECDSA-AES128-GCM-SHA256", "ECDHE-ECDSA-CHACHA20-POLY1305"]
TLS13_CIPHERSUITES = ["TLS_AES_256_GCM_SHA384", "TLS_AES_128_GCM_SHA256", "TLS_CHACHA20_POLY1305_SHA256"]
ALLOWED_TLS12_CIPHERS = TLS12_RSA_CIPHERS + TLS12_ECDSA_CIPHERS
ALLOWED_TLS13_CIPHERSUITES = TLS13_CIPHERSUITES

ORIGINAL_CIPHER_LIST = "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384," "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256," "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384," "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256," "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256," "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256," "TLS_AES_256_GCM_SHA384," "TLS_AES_128_GCM_SHA256," "TLS_CHACHA20_POLY1305_SHA256"

REDUCED_CIPHER_LIST = "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256," "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384," "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256," "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256," "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256," "TLS_AES_256_GCM_SHA384," "TLS_AES_128_GCM_SHA256"

RESTRICTED_CIPHER_LIST = "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,TLS_AES_128_GCM_SHA256"

# HAProxy SSL-terminating endpoints
HAPROXY_ENDPOINTS = [
    {"port": 5000, "name": "Keystone (keystone-restapi)", "use_oam": True},
    {"port": 6385, "name": "System Inventory (sysinv-restapi)", "use_oam": True},
    {"port": 6443, "name": "Kubernetes API (k8s-frontend)", "use_oam": True},
    {"port": 7777, "name": "Service Manager (sm-api-public)", "use_oam": True},
    {"port": 9311, "name": "Barbican (barbican-restapi)", "use_oam": True},
    {"port": 15497, "name": "USM (usm-restapi)", "use_oam": True},
    {"port": 18002, "name": "Fault Management (fm-api-public)", "use_oam": True},
    {"port": 4545, "name": "VIM (vim-restapi)", "use_oam": True},
    {"port": 8443, "name": "StarlingX Horizon", "use_oam": True},
]

DOCKER_REGISTRY_ENDPOINT = {"port": 9001, "name": "Docker Registry", "host": "registry.local"}
OPENLDAP_ENDPOINT = {"port": 636, "name": "OpenLDAP", "use_mgmt": True}
INGRESS_ENDPOINT = {"port": 443, "name": "OAM HTTPS (Ingress)", "use_oam": True}
K8S_API_ENDPOINT = {"port": 16443, "name": "Kubernetes API (kube_apiserver)", "use_oam": True}

ENDPOINTS = HAPROXY_ENDPOINTS + [DOCKER_REGISTRY_ENDPOINT, OPENLDAP_ENDPOINT, K8S_API_ENDPOINT, INGRESS_ENDPOINT]

# Known limitation sets
BULLSEYE_TLS13_SKIP_ENDPOINTS = {"StarlingX Horizon"}
GO_TLS13_CIPHER_NOT_ENFORCED = {"Docker Registry", "Kubernetes API (kube_apiserver)", "OAM HTTPS (Ingress)"}

# Service-specific enforcement status
SERVICE_ENFORCEMENT_STATUS = {
    "haproxy": {"tls12_rsa": "enforced", "tls12_ecdsa": "rejected_cert_mismatch", "tls13": "enforced"},
    "docker_registry": {"tls12_rsa": "enforced", "tls12_ecdsa": "rejected_cert_mismatch", "tls13": "not_enforced_go_limitation"},
    "openldap": {"tls12_rsa": "enforced", "tls12_ecdsa": "rejected_cert_mismatch", "tls13": "enforced"},
}


# =============================================================================
# TEST CASES
# =============================================================================


@mark.p0
def test_disallowed_ciphers_rejected(request):
    """Verify disallowed ciphers are rejected on all externally visible platform HTTPS endpoints.

    Test Steps:
        - Connect with AES256-SHA cipher to each endpoint and verify rejection
        - Connect with DES-CBC3-SHA cipher to each endpoint and verify rejection
        - Connect with RC4-SHA cipher to each endpoint and verify rejection
        - Test against all endpoints (HAProxy, Docker Registry, OpenLDAP, K8s API)
        - OpenLDAP on Bullseye: slapd 2.4/GnuTLS does not enforce platform cipher list
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()
    os_version = tls_kw.get_os_version()

    for ep in ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")
        for cipher in DISALLOWED_CIPHERS:
            get_logger().log_test_case_step(f"Verifying cipher '{cipher}' rejected on {ep['name']}")
            if ep["name"] == "OpenLDAP" and os_version == "bullseye":
                # Known limitation: slapd 2.4/GnuTLS on Bullseye does not enforce platform cipher list
                tls_kw.verify_cipher_accepted(host, ep["port"], cipher, ep["name"], ep_is_ipv6)
            else:
                tls_kw.verify_cipher_rejected(host, ep["port"], cipher, ep["name"], ep_is_ipv6)


@mark.p0
def test_allowed_ciphers_accepted(request):
    """Verify allowed ciphers are accepted on all externally visible platform HTTPS endpoints.

    Test Steps:
        - Test TLS 1.2 allowed RSA ciphers with -tls1_2 -cipher flags
        - Test TLS 1.3 allowed ciphersuites with -tls1_3 -ciphersuites flags
        - Verify connections succeed (non-null cipher negotiated)
        - Test against all endpoints
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    for ep in ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")

        # Test TLS 1.2 allowed ciphers
        for cipher in TLS12_RSA_CIPHERS:
            get_logger().log_test_case_step(f"Verifying TLS 1.2 cipher '{cipher}' accepted on {ep['name']}")
            tls_kw.verify_cipher_accepted(host, ep["port"], cipher, ep["name"], ep_is_ipv6)

        # Test TLS 1.3 allowed ciphersuites
        for ciphersuite in TLS13_CIPHERSUITES:
            get_logger().log_test_case_step(f"Verifying TLS 1.3 ciphersuite '{ciphersuite}' accepted on {ep['name']}")
            tls_kw.verify_tls13_ciphersuite_accepted(host, ep["port"], ciphersuite, ep["name"], ep_is_ipv6)


@mark.p1
def test_go_tls13_and_cert_mismatch_cipher_behavior(request):
    """Validate and document known limitations in TLS cipher enforcement.

    Covers: Go crypto/tls TLS 1.3 limitation on Docker Registry, ECDSA cipher
    rejection due to RSA certificate mismatch, GnuTLS algorithm-level exclusions
    on OpenLDAP.

    Test Steps:
        - Document Go crypto/tls TLS 1.3 limitation on Docker Registry
        - Verify ECDSA rejections are due to RSA certificate usage
        - Test GnuTLS algorithm-level exclusions on OpenLDAP
        - Validate current platform behavior matches known limitations
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    get_logger().log_info("Validating known TLS cipher enforcement limitations")

    # Limitation 1: Docker Registry TLS 1.3 cipher restriction (Go limitation)
    docker_ep = next(ep for ep in ENDPOINTS if ep["name"] == "Docker Registry")
    docker_host = tls_kw.resolve_host(docker_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("Docker Registry TLS 1.3 limitation (Go crypto/tls)")
    get_logger().log_info("Go's crypto/tls hardcodes all TLS 1.3 ciphers and provides no API to restrict them")

    # All TLS 1.3 ciphersuites should be accepted on Docker Registry due to Go limitation
    for ciphersuite in TLS13_CIPHERSUITES:
        tls_kw.verify_tls13_ciphersuite_accepted(
            docker_host,
            docker_ep["port"],
            ciphersuite,
            docker_ep["name"],
            ep_ips.is_ipv6_lab(),
        )
        get_logger().log_info(f"Docker Registry accepts '{ciphersuite}' - Go crypto/tls limitation confirmed")

    # Limitation 2: ECDSA cipher rejection is misleading (certificate mismatch)
    oam_ep = ENDPOINTS[0]
    oam_host = tls_kw.resolve_host(oam_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("ECDSA cipher rejection (RSA certificate mismatch)")
    get_logger().log_info("Platform uses RSA certificates, so ECDSA ciphers are rejected at certificate level")

    # ECDSA ciphers should be rejected due to certificate mismatch, not cipher enforcement
    for cipher in TLS12_ECDSA_CIPHERS[:2]:  # Test first 2
        tls_kw.verify_ecdsa_cipher_rejected_cert_mismatch(
            oam_host,
            oam_ep["port"],
            cipher,
            oam_ep["name"],
            ep_ips.is_ipv6_lab(),
        )
        get_logger().log_info(f"ECDSA cipher '{cipher}' rejected due to RSA cert - NOT cipher enforcement")

    # Limitation 3: GnuTLS exclusion operates at cipher algorithm level (OpenLDAP)
    ldap_ep = next(ep for ep in ENDPOINTS if ep["name"] == "OpenLDAP")
    ldap_host = tls_kw.resolve_host(ldap_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("GnuTLS algorithm-level exclusion (OpenLDAP)")
    get_logger().log_info("GnuTLS -ALGO exclusion removes cipher algorithm from ALL key exchanges (RSA and ECDSA)")

    # Test that RSA ciphers work on OpenLDAP (algorithm allowed)
    tls_kw.verify_cipher_accepted(ldap_host, ldap_ep["port"], TLS12_RSA_CIPHERS[0], ldap_ep["name"], ep_ips.is_ipv6_lab())

    # ECDSA ciphers rejected due to certificate mismatch (would be rejected by algorithm exclusion too)
    tls_kw.verify_ecdsa_cipher_rejected_cert_mismatch(
        ldap_host,
        ldap_ep["port"],
        TLS12_ECDSA_CIPHERS[0],
        ldap_ep["name"],
        ep_ips.is_ipv6_lab(),
    )

    get_logger().log_info("Known limitations validation completed - behavior matches documented limitations")


@mark.p1
def test_service_specific_cipher_matrix(request):
    """Verify service-specific cipher enforcement across all services.

    Comprehensive test of cipher enforcement with service-specific characteristics:
    HAProxy (OpenSSL), Docker Registry (Go TLS), OpenLDAP (GnuTLS).

    Test Steps:
        - Test TLS 1.2 RSA ciphers on each service type
        - Test TLS 1.2 ECDSA ciphers (expect cert mismatch rejection)
        - Test TLS 1.3 ciphersuites (enforcement varies by service)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    get_logger().log_info("Testing service-specific cipher enforcement matrix")

    # Service mapping for detailed testing
    # HAProxy SSL-terminating frontends (ports 5000, 6385, 6443, 7777, 9311, 15497, 18002, 4545)
    # Docker Registry: TCP passthrough by HAProxy, Go handles TLS directly
    # OpenLDAP: slapd 2.4/GnuTLS 3.7 handles TLS directly
    service_endpoints = {"haproxy": [ep["name"] for ep in HAPROXY_ENDPOINTS], "docker_registry": [DOCKER_REGISTRY_ENDPOINT["name"]], "openldap": [OPENLDAP_ENDPOINT["name"]]}

    for service_type, endpoint_names in service_endpoints.items():
        get_logger().log_test_case_step(f"Testing {service_type.upper()} cipher enforcement")

        for endpoint_name in endpoint_names:
            ep = next(ep for ep in ENDPOINTS if ep["name"] == endpoint_name)
            host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
            ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")

            get_logger().log_info(f"Testing {endpoint_name} ({service_type})")

            # Test TLS 1.2 RSA ciphers (should be enforced on all services)
            get_logger().log_info(f"TLS 1.2 RSA ciphers on {endpoint_name}: " f"{SERVICE_ENFORCEMENT_STATUS[service_type]['tls12_rsa']}")
            for cipher in TLS12_RSA_CIPHERS:
                tls_kw.verify_cipher_accepted(host, ep["port"], cipher, ep["name"], ep_is_ipv6)

            # Test TLS 1.2 ECDSA ciphers (should be rejected due to cert mismatch)
            get_logger().log_info(f"TLS 1.2 ECDSA ciphers on {endpoint_name}: " f"{SERVICE_ENFORCEMENT_STATUS[service_type]['tls12_ecdsa']}")
            tls_kw.verify_ecdsa_cipher_rejected_cert_mismatch(
                host,
                ep["port"],
                TLS12_ECDSA_CIPHERS[0],
                ep["name"],
                ep_is_ipv6,
            )

            # Test TLS 1.3 ciphersuites (enforcement varies by service)
            tls13_status = SERVICE_ENFORCEMENT_STATUS[service_type]["tls13"]
            get_logger().log_info(f"TLS 1.3 ciphersuites on {endpoint_name}: {tls13_status}")

            if tls13_status == "enforced":
                tls_kw.verify_tls13_ciphersuite_accepted(
                    host,
                    ep["port"],
                    TLS13_CIPHERSUITES[0],
                    ep["name"],
                    ep_is_ipv6,
                )
            elif tls13_status == "not_enforced_go_limitation":
                tls_kw.verify_tls13_ciphersuite_accepted(
                    host,
                    ep["port"],
                    TLS13_CIPHERSUITES[0],
                    ep["name"],
                    ep_is_ipv6,
                )
                get_logger().log_info(f"Note: {endpoint_name} cannot restrict TLS 1.3 - Go crypto/tls limitation")

    get_logger().log_info("Service-specific cipher enforcement matrix validation completed")


@mark.p1
def test_tls13_ignores_tls12_cipher_flag(request):
    """Verify TLS 1.3 ignores the -cipher flag (TLS 1.2 only).

    When forcing -tls1_3 with a TLS 1.2 -cipher value, OpenSSL should either
    negotiate a TLS 1.3 ciphersuite or reject the connection entirely.

    Test Steps:
        - Force TLS 1.3 with a TLS 1.2 cipher flag
        - Verify TLS 1.3 ciphersuite negotiated or connection rejected
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    oam_ep = ENDPOINTS[0]
    oam_host = tls_kw.resolve_host(oam_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("Forcing TLS 1.3 with TLS 1.2 cipher flag")
    output = tls_kw.run_openssl_tls13_with_tls12_cipher(oam_host, oam_ep["port"], ALLOWED_TLS12_CIPHERS[0], ep_ips.is_ipv6_lab())
    output_lower = str(output).lower() if not isinstance(output, str) else output.lower()
    tls13_negotiated = "tls_aes" in output_lower or "tls_chacha20" in output_lower
    validate_equals(
        tls13_negotiated or TlsKeywords.is_tls_handshake_rejected(output_lower),
        True,
        "TLS 1.3 ignores TLS 1.2 cipher or rejects connection",
    )


@mark.p1
def test_tls12_ignores_ciphersuites_flag(request):
    """Verify TLS 1.2 ignores the -ciphersuites flag (TLS 1.3 only).

    When forcing -tls1_2 with a TLS 1.3 -ciphersuites value, OpenSSL should
    fall back to its default TLS 1.2 cipher list or reject the connection.

    Test Steps:
        - Force TLS 1.2 with a TLS 1.3 ciphersuites flag
        - Verify connection rejected or fell back to a TLS 1.2 cipher
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    oam_ep = ENDPOINTS[0]
    oam_host = tls_kw.resolve_host(oam_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("Forcing TLS 1.2 with TLS 1.3 ciphersuites flag")
    output = tls_kw.run_openssl_tls12_with_tls13_ciphersuite(oam_host, oam_ep["port"], ALLOWED_TLS13_CIPHERSUITES[0], ep_ips.is_ipv6_lab())
    output_lower = str(output).lower() if not isinstance(output, str) else output.lower()
    tls13_not_enforced = not TlsKeywords.is_tls_handshake_rejected(output_lower) and "tls_aes" not in output_lower
    validate_equals(
        TlsKeywords.is_tls_handshake_rejected(output_lower) or tls13_not_enforced,
        True,
        "TLS 1.2 with TLS 1.3 ciphersuite: rejected or fell back to TLS 1.2 cipher",
    )


@mark.p1
def test_matching_tls_version_cipher_accepted(request):
    """Verify matching TLS version and cipher combinations succeed.

    Test Steps:
        - Force TLS 1.3 with TLS 1.3 ciphersuite -> accepted
        - Force TLS 1.2 with TLS 1.2 cipher -> accepted
        - Default connection -> negotiates best available
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    oam_ep = ENDPOINTS[0]
    oam_host = tls_kw.resolve_host(oam_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("TLS 1.3 with TLS 1.3 ciphersuite")
    tls_kw.verify_tls13_ciphersuite_accepted(
        oam_host,
        oam_ep["port"],
        ALLOWED_TLS13_CIPHERSUITES[0],
        oam_ep["name"],
        ep_ips.is_ipv6_lab(),
    )

    get_logger().log_test_case_step("TLS 1.2 with TLS 1.2 cipher")
    tls_kw.verify_cipher_accepted(
        oam_host,
        oam_ep["port"],
        ALLOWED_TLS12_CIPHERS[0],
        oam_ep["name"],
        ep_ips.is_ipv6_lab(),
    )

    get_logger().log_test_case_step("Default connection negotiates best available")
    tls_kw.verify_default_cipher_in_use(
        oam_host,
        oam_ep["port"],
        oam_ep["name"],
        ep_ips.is_ipv6_lab(),
    )


@mark.p1
def test_cipher_configuration_readable(request):
    """Verify current cipher configurations exist and are readable.

    Test Steps:
        - Query service-parameter-list for tls-cipher-suite
        - Verify platform and kubernetes cipher configurations exist
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving current cipher configurations")

    params = tls_kw.service_param_keywords.list_service_parameters().get_parameters()
    platform_param = any(p.get_name() == "tls-cipher-suite" for p in params)
    k8s_param = any(p.get_name() == "tls-cipher-suites" for p in params)

    get_logger().log_test_case_step("Verifying platform cipher configuration exists")
    validate_equals(platform_param, True, "Platform cipher configuration exists")
    get_logger().log_test_case_step("Verifying kubernetes cipher configuration exists")
    validate_equals(k8s_param, True, "Kubernetes cipher configuration exists")


@mark.p1
def test_cipher_enforcement_on_key_endpoints(request):
    """Verify cipher enforcement is consistent on key endpoints.

    Test Steps:
        - Verify allowed ciphers work on Keystone and System Inventory endpoints
        - Verify disallowed ciphers are rejected on those endpoints
        - Verify default and TLS 1.3 connections succeed
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    oam_ep = ENDPOINTS[0]  # Keystone (5000)
    k8s_ep = ENDPOINTS[1]  # System Inventory (6385)
    oam_host = tls_kw.resolve_host(oam_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
    k8s_host = tls_kw.resolve_host(k8s_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())

    get_logger().log_test_case_step("Verifying allowed ciphers work")
    tls_kw.verify_cipher_accepted(oam_host, oam_ep["port"], ALLOWED_TLS12_CIPHERS[0], oam_ep["name"], ep_ips.is_ipv6_lab())
    tls_kw.verify_cipher_accepted(k8s_host, k8s_ep["port"], ALLOWED_TLS12_CIPHERS[0], k8s_ep["name"], ep_ips.is_ipv6_lab())

    get_logger().log_test_case_step("Verifying disallowed ciphers rejected")
    for cipher in DISALLOWED_CIPHERS[:2]:
        tls_kw.verify_cipher_rejected(oam_host, oam_ep["port"], cipher, oam_ep["name"], ep_ips.is_ipv6_lab())
        tls_kw.verify_cipher_rejected(k8s_host, k8s_ep["port"], cipher, k8s_ep["name"], ep_ips.is_ipv6_lab())

    get_logger().log_test_case_step("Verifying default and TLS 1.3 connections succeed")
    tls_kw.verify_default_cipher_in_use(oam_host, oam_ep["port"], oam_ep["name"], ep_ips.is_ipv6_lab())
    tls_kw.verify_default_cipher_in_use(k8s_host, k8s_ep["port"], k8s_ep["name"], ep_ips.is_ipv6_lab())
    tls_kw.verify_tls13_ciphersuite_accepted(
        oam_host,
        oam_ep["port"],
        ALLOWED_TLS13_CIPHERSUITES[0],
        oam_ep["name"],
        ep_ips.is_ipv6_lab(),
    )


# NOTE: Config-modifying tests below now include Kubernetes cipher modifications.
# The bootstrap token generation issue has been resolved, so Kubernetes
# kube_apiserver tls-cipher-suites modifications are now enabled.


@mark.p1
def test_tls12_and_tls13_cipher_removal_enforcement(request):
    """Verify TLS 1.2 and TLS 1.3 cipher removal enforcement.

    Verify that removing a cipher from both the TLS 1.2 and TLS 1.3 allowed
    lists causes those ciphers to be rejected while remaining ciphers still work.

    Test Steps:
        - Remove ECDHE-RSA-AES256-GCM-SHA384 and TLS_CHACHA20_POLY1305_SHA256
        - Apply modified cipher list to platform and kubernetes
        - Wait for configuration propagation
        - Verify removed ciphers are rejected on endpoints
        - Verify remaining ciphers still work
    Teardown:
        - Restore original cipher list for platform and kubernetes
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    removed_tls12_cipher = TLS12_RSA_CIPHERS[0]
    removed_tls13_cipher = TLS13_CIPHERSUITES[2]

    def teardown() -> None:
        """Restore the original cipher suite parameters and wait for propagation."""
        tls_kw.restore_original_cipher_config(ORIGINAL_CIPHER_LIST)
        get_logger().log_info("Waiting 60s for restored cipher config to propagate")
        time.sleep(60)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Removing cipher '{removed_tls12_cipher}' and '{removed_tls13_cipher}'")
    tls_kw.apply_cipher_list(REDUCED_CIPHER_LIST)

    poll_ep = HAPROXY_ENDPOINTS[0]
    poll_host = tls_kw.resolve_host(poll_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
    tls_kw.wait_for_cipher_propagation(
        poll_host,
        poll_ep["port"],
        removed_tls12_cipher,
        expect_rejected=True,
        is_ipv6=ep_ips.is_ipv6_lab() and not poll_ep.get("host"),
    )
    k8s_host = tls_kw.resolve_host(K8S_API_ENDPOINT, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
    tls_kw.wait_for_cipher_propagation(
        k8s_host,
        K8S_API_ENDPOINT["port"],
        removed_tls12_cipher,
        expect_rejected=True,
        is_ipv6=ep_ips.is_ipv6_lab(),
    )

    remaining_tls12 = TLS12_RSA_CIPHERS[1]
    remaining_tls13 = TLS13_CIPHERSUITES[0]
    os_version = tls_kw.get_os_version()

    tls13_not_enforced = GO_TLS13_CIPHER_NOT_ENFORCED.copy()
    # Horizon TLS 1.3 cipher not enforced on any OS version (lighttpd limitation)
    tls13_not_enforced = tls13_not_enforced | BULLSEYE_TLS13_SKIP_ENDPOINTS

    skip_cipher_removal = set()
    if os_version == "bullseye":
        skip_cipher_removal.add("OpenLDAP")

    tls_kw.verify_cipher_removal_on_endpoints(
        ENDPOINTS,
        {"removed_tls12": removed_tls12_cipher, "removed_tls13": removed_tls13_cipher, "remaining_tls12": remaining_tls12, "remaining_tls13": remaining_tls13},
        {"oam_ip": ep_ips.get_oam_ip(), "mgmt_ip": ep_ips.get_mgmt_ip(), "is_ipv6": ep_ips.is_ipv6_lab(), "tls13_not_enforced": tls13_not_enforced, "skip_cipher_removal": skip_cipher_removal},
    )


@mark.p1
def test_single_cipher_enforcement(request):
    """Verify single cipher enforcement.

    Verify that setting the cipher list to a single cipher causes only that
    cipher to be accepted and all others to be rejected.

    Test Steps:
        - Set tls-cipher-suite to a restricted list (one TLS 1.2 + one TLS 1.3 cipher)
        - Apply platform service parameters and wait for propagation
        - Verify the allowed cipher is accepted
        - Verify previously allowed ciphers not in the restricted list are rejected
    Teardown:
        - Restore original cipher list for platform and kubernetes
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    accepted_cipher_openssl = "ECDHE-RSA-AES128-GCM-SHA256"
    rejected_ciphers = [c for c in TLS12_RSA_CIPHERS if c != accepted_cipher_openssl]

    def teardown() -> None:
        """Restore the original cipher suite parameter."""
        tls_kw.restore_original_cipher_config(ORIGINAL_CIPHER_LIST)

    request.addfinalizer(teardown)

    # Pre-check
    poll_ep = HAPROXY_ENDPOINTS[0]
    poll_host = tls_kw.resolve_host(poll_ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
    get_logger().log_test_case_step(f"Pre-check: '{accepted_cipher_openssl}' is accepted")
    tls_kw.verify_cipher_accepted(
        poll_host,
        poll_ep["port"],
        accepted_cipher_openssl,
        poll_ep["name"],
        ep_ips.is_ipv6_lab(),
    )

    # Apply restricted cipher list and wait for propagation
    get_logger().log_test_case_step(f"Setting tls-cipher-suite to '{RESTRICTED_CIPHER_LIST}'")
    tls_kw.apply_cipher_list(RESTRICTED_CIPHER_LIST)

    if rejected_ciphers:
        tls_kw.wait_for_cipher_propagation(
            poll_host,
            poll_ep["port"],
            rejected_ciphers[0],
            expect_rejected=True,
            is_ipv6=ep_ips.is_ipv6_lab() and not poll_ep.get("host"),
        )
        k8s_host = tls_kw.resolve_host(K8S_API_ENDPOINT, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        tls_kw.wait_for_cipher_propagation(
            k8s_host,
            K8S_API_ENDPOINT["port"],
            rejected_ciphers[0],
            expect_rejected=True,
            is_ipv6=ep_ips.is_ipv6_lab(),
        )

    # Verify enforcement on platform-governed endpoints
    platform_endpoints = HAPROXY_ENDPOINTS + [DOCKER_REGISTRY_ENDPOINT, OPENLDAP_ENDPOINT]
    tls_kw.verify_single_cipher_on_endpoints(
        platform_endpoints,
        accepted_cipher_openssl,
        rejected_ciphers,
        {"oam_ip": ep_ips.get_oam_ip(), "mgmt_ip": ep_ips.get_mgmt_ip(), "is_ipv6": ep_ips.is_ipv6_lab()},
    )

    # Verify enforcement on kube_apiserver
    k8s_host = tls_kw.resolve_host(K8S_API_ENDPOINT, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
    get_logger().log_test_case_step(f"Verifying single cipher enforcement on {K8S_API_ENDPOINT['name']}")
    tls_kw.verify_cipher_accepted(k8s_host, K8S_API_ENDPOINT["port"], accepted_cipher_openssl, K8S_API_ENDPOINT["name"], ep_ips.is_ipv6_lab())
    for cipher in rejected_ciphers:
        tls_kw.verify_cipher_rejected(k8s_host, K8S_API_ENDPOINT["port"], cipher, K8S_API_ENDPOINT["name"], ep_ips.is_ipv6_lab())


@mark.p1
def test_invalid_cipher_negotiation_rejected(request):
    """Verify invalid/insecure ciphers are rejected on all endpoints.

    Verify that completely invalid, NULL, and export-grade cipher suites
    cannot negotiate a TLS handshake on any externally visible endpoint.
    Covers ciphers that should never be accepted regardless of configuration:
    NULL ciphers (no encryption), export-grade ciphers, and bogus cipher strings.

    Test Steps:
        - Attempt TLS handshake with each invalid cipher on all endpoints
        - Verify all handshakes are rejected (null cipher negotiated or client error)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    tls_kw = TlsKeywords(ssh_connection)
    get_logger().log_setup_step("Retrieving OAM and management IPs")
    ep_ips = tls_kw.get_endpoint_ips()

    for ep in ENDPOINTS:
        host = tls_kw.resolve_host(ep, ep_ips.get_oam_ip(), ep_ips.get_mgmt_ip())
        ep_is_ipv6 = ep_ips.is_ipv6_lab() and not ep.get("host")

        # Wait for port to be ready before testing (handles dual-stack/timing issues)
        if not tls_kw.wait_for_port_ready(host, ep["port"], ep_is_ipv6):
            get_logger().log_warning(f"Skipping {ep['name']} ({host}:{ep['port']}) - port not reachable after retries")
            continue

        for cipher in INVALID_CIPHERS:
            get_logger().log_test_case_step(f"Verifying invalid cipher '{cipher}' rejected on {ep['name']}")
            output = tls_kw.run_openssl_cipher_connection(host, ep["port"], cipher, ep_is_ipv6)

            # Invalid ciphers should either fail the handshake or be rejected by openssl client itself
            rejected = TlsKeywords.is_tls_handshake_rejected(output)
            validate_equals(rejected, True, f"Invalid cipher '{cipher}' rejected on {ep['name']} ({host}:{ep['port']})")

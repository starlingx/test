"""Unit tests for IPSecSecurityAssociationOutput and endpoint IP/CN parsing.

Validates security-association parsing from swanctl --list-sa output, including
the endpoint IP extraction added for CGCS parity (local/remote IP validation).
The management addresses below are StarlingX internal mgmt-network sample values
(192.168.204.0/24) used only as representative parser input.
"""

from keywords.cloud_platform.security.objects.ipsec_security_association_output import IPSecSecurityAssociationOutput

# Sample swanctl --list-sa output with two IKE SA blocks (2 per remote host).
SAMPLE_SA_OUTPUT = [
    "system-nodes: #1, ESTABLISHED, IKEv2, abcd1234@192.168.204.2 ...",
    "  local  'CN=ipsec-controller-0' @ 192.168.204.2[500]",
    "  remote 'CN=ipsec-controller-1' @ 192.168.204.3[500]",
    "  node: #1, INSTALLED, TRANSPORT",
    "system-nodes: #2, ESTABLISHED, IKEv2, ef567890@192.168.204.2 ...",
    "  local  'CN=ipsec-controller-0' @ 192.168.204.2[500]",
    "  remote 'CN=ipsec-worker-0' @ 192.168.204.4[500]",
    "  node: #2, INSTALLED, TRANSPORT",
]

# Management IP set the sample endpoints are expected to belong to.
SAMPLE_MGMT_IPS = {"192.168.204.2", "192.168.204.3", "192.168.204.4"}


def test_parses_two_associations():
    """Two system-nodes blocks are parsed into two associations."""
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)
    assert len(output.get_associations()) == 2


def test_associations_are_established():
    """Both parsed associations are detected as ESTABLISHED."""
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)
    assert all(assoc.is_established() for assoc in output.get_associations())


def test_local_and_remote_cns_parsed():
    """Local and remote CNs are extracted from each association."""
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)
    first = output.get_associations()[0]

    assert first.has_local_cn_starting_with("ipsec-controller-0") is True
    assert first.has_remote_cn_in_set({"ipsec-controller-1"}) is True


def test_endpoint_ips_parsed():
    """Local and remote endpoint IPs are extracted from each association."""
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)
    first = output.get_associations()[0]

    assert first.get_local_ips() == ["192.168.204.2"]
    assert first.get_remote_ips() == ["192.168.204.3"]


def test_endpoint_ips_validate_against_mgmt_set():
    """Endpoint IPs validate against the known management IP set."""
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)

    for assoc in output.get_associations():
        assert assoc.has_local_ip_in_set(SAMPLE_MGMT_IPS) is True
        assert assoc.has_all_remote_ips_in_set(SAMPLE_MGMT_IPS) is True


def test_endpoint_ips_validate_against_mgmt_subnet():
    """Endpoint IPs validate against the management subnet (handles floating IPs)."""
    subnet = "192.168.204.0/24"
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)

    for assoc in output.get_associations():
        assert assoc.has_local_ip_in_subnet(subnet) is True
        assert assoc.has_all_remote_ips_in_subnet(subnet) is True


def test_ipv6_endpoint_ips_validate_against_subnet():
    """IPv6 endpoint IPs (including a floating-style local address) validate by subnet.

    Mirrors the AIO-DX IPv6 case where the active controller's local endpoint is
    the management floating address, which is not a per-host unit address.
    """
    ipv6_sa_output = [
        "system-nodes: #1, ESTABLISHED, IKEv2, aa@fdff:10:80:18::2",
        "  local  'CN=ipsec-controller-0' @ fdff:10:80:18::2[500]",
        "  remote 'CN=ipsec-controller-1' @ fdff:10:80:18::4[500]",
        "system-nodes: #2, ESTABLISHED, IKEv2, bb@fdff:10:80:18::3",
        "  local  'CN=ipsec-controller-0' @ fdff:10:80:18::3[500]",
        "  remote 'CN=ipsec-compute-0' @ fdff:10:80:18::5a8[500]",
    ]
    subnet = "fdff:10:80:18::/64"
    output = IPSecSecurityAssociationOutput(ipv6_sa_output)

    assert len(output.get_associations()) == 2
    for assoc in output.get_associations():
        assert assoc.has_local_ip_in_subnet(subnet) is True
        assert assoc.has_all_remote_ips_in_subnet(subnet) is True


def test_remote_ip_outside_subnet_fails():
    """A remote endpoint IP outside the management subnet is rejected."""
    foreign_sa_output = [
        "system-nodes: #1, ESTABLISHED, IKEv2, aa@192.168.204.2",
        "  local  'CN=ipsec-controller-0' @ 192.168.204.2[500]",
        "  remote 'CN=ipsec-rogue' @ 10.0.0.9[500]",
    ]
    output = IPSecSecurityAssociationOutput(foreign_sa_output)

    assoc = output.get_associations()[0]
    assert assoc.has_all_remote_ips_in_subnet("192.168.204.0/24") is False


def test_remote_ip_not_in_mgmt_set_fails():
    """A remote IP outside the management set is rejected."""
    restricted_mgmt_ips = {"192.168.204.2", "192.168.204.3"}  # worker 204.4 intentionally absent
    output = IPSecSecurityAssociationOutput(SAMPLE_SA_OUTPUT)

    # Second association's remote (worker-0 @ 204.4) is not in the restricted set.
    second = output.get_associations()[1]
    assert second.has_all_remote_ips_in_set(restricted_mgmt_ips) is False


def test_empty_output_has_no_associations():
    """Empty output yields no associations."""
    assert len(IPSecSecurityAssociationOutput([]).get_associations()) == 0

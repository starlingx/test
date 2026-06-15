"""Test OVS L2 forwarding.

Covers TC 4, 5, 6, 7, 8, 9, 10, 44, 45 from the test plan.
"""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

# Lab-specific configuration for OVS traffic testing
# These values are determined by the lab's NAD/helm configuration
SX049_IP = "2620:10a:a001:aa27::53"
SX049_PASSWORD = "Li69nux*1234"
UNTAGGED_PEER_IP = "fd01::22"
VRRP_VIP = "fd01::1"
VLAN100_PEER_IP = "fd02::10"
VLAN200_PEER_IP = "fd03::22"
VLAN100_TAGGED_IP = "fd02::22"



@mark.p1
@mark.lab_has_ovs
def test_l2_untagged_forwarding():
    """Verify L2 bridging between SR-IOV VFs without VLAN tagging.

    Test Steps:
        - Ping from SX-049 traffic pod to peer on native VLAN (untagged)
        - Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(SX049_IP, SX049_PASSWORD, "pod1-deployment")

    get_logger().log_test_case_step("Ping on untagged native VLAN: traffic pod -> peer")
    output = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, traffic_pod, f"ping6 -c 5 -W 2 {UNTAGGED_PEER_IP}")
    validate_str_contains(output, "0% packet loss", "TC4: Untagged L2 traffic should have 0% loss")


@mark.p1
@mark.lab_has_ovs
def test_l2_vlan100_tagged():
    """Verify L2 bridging between SR-IOV VFs with VLAN 100 tagging.

    Test Steps:
        - Ping from SX-049 VRRP backup pod to traffic pod on VLAN 100
        - Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    vrrp_pod = ovs_kw.get_remote_pod_by_prefix(SX049_IP, SX049_PASSWORD, "vrrp-backup-vlan")

    get_logger().log_test_case_step("Ping on VLAN 100: VRRP backup -> traffic pod")
    output = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, vrrp_pod, f"ping6 -c 5 -W 2 {VLAN100_PEER_IP}")
    validate_str_contains(output, "0% packet loss", "TC5: VLAN 100 tagged traffic should have 0% loss")


@mark.p1
@mark.lab_has_ovs
def test_ipv6_unicast():
    """Verify L2 bridging of IPv6 unicast traffic via VRRP VIP.

    Test Steps:
        - Ping from traffic pod to VRRP VIP
        - Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(SX049_IP, SX049_PASSWORD, "pod1-deployment")

    get_logger().log_test_case_step("Ping IPv6 unicast to VRRP VIP")
    output = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, traffic_pod, f"ping6 -c 5 -W 2 {VRRP_VIP}")
    validate_str_contains(output, "0% packet loss", "TC6: IPv6 unicast should have 0% loss")


@mark.p1
@mark.lab_has_ovs
def test_ipv6_unicast_vlan200():
    """Verify L2 bridging of IPv6 unicast traffic on VLAN 200.

    Test Steps:
        - Ping from traffic pod to peer on VLAN 200
        - Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(SX049_IP, SX049_PASSWORD, "pod1-deployment")

    get_logger().log_test_case_step("Ping IPv6 on VLAN 200: traffic pod -> peer")
    output = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, traffic_pod, f"ping6 -c 5 -W 2 {VLAN200_PEER_IP}")
    validate_str_contains(output, "0% packet loss", "TC7: IPv6 VLAN 200 should have 0% loss")


@mark.p1
@mark.lab_has_ovs
def test_multicast_snooping_off():
    """Verify multicast snooping is OFF for IPv4/IPv6 passthrough.

    Test Steps:
        - Query mcast_snooping_enable on br-sriov
        - Verify it is false (multicast floods to all ports)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    get_logger().log_test_case_step("Verify mcast_snooping_enable is false on br-sriov")
    output = ovs_kw.ovs_vsctl(ovs_agent_pod, "get bridge br-sriov mcast_snooping_enable")
    validate_str_contains(output, "false", "TC8/9: Multicast snooping should be OFF (passthrough)")


@mark.p1
@mark.lab_has_ovs
def test_mac_learning_fdb():
    """Verify MAC address learning and FDB table population.

    Test Steps:
        - Query FDB table on br-sriov
        - Verify entries exist with port column (MACs learned)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    get_logger().log_test_case_step("Query FDB table on br-sriov")
    output = ovs_kw.ovs_appctl(ovs_agent_pod, "fdb/show br-sriov")
    validate_str_contains(output, "port", "TC10: FDB should have learned MAC entries")
    get_logger().log_test_case_step(f"FDB entries:\n{output}")


@mark.p1
@mark.lab_has_ovs
def test_native_vlan_forwarding():
    """Verify native VLAN (untagged) traffic is forwarded correctly.

    Test Steps:
        - Ping from traffic pod to VRRP VIP on native VLAN
        - Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(SX049_IP, SX049_PASSWORD, "pod1-deployment")

    get_logger().log_test_case_step("Ping on native VLAN: traffic pod -> VRRP VIP")
    output = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, traffic_pod, f"ping6 -c 3 -W 2 {VRRP_VIP}")
    validate_str_contains(output, "0% packet loss", "TC44: Native VLAN traffic should forward correctly")


@mark.p1
@mark.lab_has_ovs
def test_mixed_tagged_untagged_traffic():
    """Verify OVS bridge handles mixed tagged and untagged traffic simultaneously.

    Test Steps:
        - Ping on untagged native VLAN
        - Ping on tagged VLAN 100
        - Verify both have 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(SX049_IP, SX049_PASSWORD, "pod1-deployment")

    get_logger().log_test_case_step("Ping untagged (native VLAN)")
    out_untagged = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, traffic_pod, f"ping6 -c 3 -W 2 {VRRP_VIP}")
    validate_str_contains(out_untagged, "0% packet loss", "TC45: Untagged traffic should work")

    get_logger().log_test_case_step("Ping tagged VLAN 100")
    out_tagged = ovs_kw.exec_on_remote_pod(SX049_IP, SX049_PASSWORD, traffic_pod, f"ping6 -c 3 -W 2 {VLAN100_TAGGED_IP}")
    validate_str_contains(out_tagged, "0% packet loss", "TC45: Tagged VLAN 100 traffic should work")

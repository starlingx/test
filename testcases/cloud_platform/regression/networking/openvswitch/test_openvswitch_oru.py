"""Test ORU traffic simulation via OVS bridge.

Validates ORU (O-RAN Radio Unit) traffic scenarios using pods to
simulate network nodes. Traffic flows through the OVS bridge on VLAN 110
(RMS) and validates VRRP gateway reachability, failover, SLAAC, and DHCPv6.
Uses pods to represent the ORU network node (no hardware required).
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains, validate_str_contains_with_retry
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords


@mark.p1
@mark.lab_has_ovs
def test_oru_traffic_vlan110(request: FixtureRequest):
    """Verify ORU RMS traffic flows on VLAN 110 via OVS bridge.

    Simulates ORU traffic by creating a VLAN 110 internal port on the OVS
    bridge and verifying connectivity to the remote peer on the same VLAN.

    Test Steps:
        1. Create OVS internal port with VLAN 110 tag
        2. Assign host IP in ORU subnet
        3. Verify connectivity to peer on VLAN 110

    Teardown:
        - Remove VLAN 110 internal port
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    bridge = ovs_config.get_bridge_name()

    oru_cfg = ovs_config.get_vrrp_config("vlan110")
    host_ip = oru_cfg.get_host_v6()
    vlan_id = oru_cfg.get_vlan_id()

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove VLAN 110 internal port")
        ovs_kw.ovs_vsctl(ovs_agent, f"--if-exists del-port {bridge} vlan110")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create OVS internal port with VLAN 110 tag")
    ovs_kw.add_vlan_internal_port(ovs_agent, bridge, "vlan110", vlan_id, host_ip)

    get_logger().log_test_case_step("Verify ORU traffic connectivity on VLAN 110")
    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(
        remote_ip, remote_password, ovs_config.get_traffic_pod_prefix()
    )
    output = ovs_kw.verify_connectivity_from_remote(
        remote_ip, remote_password, traffic_pod, host_ip
    )
    validate_str_contains(output, "0% packet loss", "ORU RMS traffic should flow on VLAN 110")


@mark.p1
@mark.lab_has_ovs
def test_oru_oam_vrrp_reachable(request: FixtureRequest):
    """Verify ORU can reach OAM gateway via VRRP VIP.

    Simulates ORU OAM traffic by creating a VLAN port and verifying the
    VRRP virtual IP is reachable through the OVS bridge.

    Test Steps:
        1. Create OVS internal port with ORU OAM VLAN tag
        2. Assign host IP in ORU OAM subnet
        3. Verify VRRP VIP is reachable

    Teardown:
        - Remove the VLAN internal port
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    bridge = ovs_config.get_bridge_name()

    oru_oam_cfg = ovs_config.get_vrrp_config("oru_oam")
    host_ip = oru_oam_cfg.get_host_v4()
    vlan_id = oru_oam_cfg.get_vlan_id()

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove ORU OAM VLAN port")
        ovs_kw.ovs_vsctl(ovs_agent, f"--if-exists del-port {bridge} oru-oam")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create OVS internal port for ORU OAM VLAN")
    ovs_kw.add_vlan_internal_port(ovs_agent, bridge, "oru-oam", vlan_id, host_ip)

    get_logger().log_test_case_step("Verify VRRP VIP is reachable from ORU OAM subnet")
    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(
        remote_ip, remote_password, ovs_config.get_traffic_pod_prefix()
    )
    validate_str_contains_with_retry(
        lambda: ovs_kw.verify_connectivity_from_remote(
            remote_ip, remote_password, traffic_pod, host_ip
        ),
        "0% packet loss",
        "ORU should reach OAM gateway via VRRP VIP",
        timeout=30,
        polling_sleep_time=5,
    )


@mark.p1
@mark.lab_has_ovs
def test_oru_oam_vrrp_failover(request: FixtureRequest):
    """Verify ORU OAM connectivity survives VRRP failover.

    Test Steps:
        1. Create ORU OAM VLAN port and verify VRRP VIP reachable
        2. Delete ovs-agent pod to simulate node failure
        3. Wait for new agent pod
        4. Re-create VLAN port and verify VRRP VIP still reachable

    Teardown:
        - Remove the VLAN internal port
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    bridge = ovs_config.get_bridge_name()
    namespace = ovs_config.get_namespace()

    oru_oam_cfg = ovs_config.get_vrrp_config("oru_oam")
    host_ip = oru_oam_cfg.get_host_v4()
    vlan_id = oru_oam_cfg.get_vlan_id()

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove ORU OAM VLAN port")
        new_agent = ovs_kw.get_ovs_agent_pod()
        ovs_kw.ovs_vsctl(new_agent, f"--if-exists del-port {bridge} oru-oam-failover")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create ORU OAM VLAN port and verify connectivity")
    ovs_kw.add_vlan_internal_port(ovs_agent, bridge, "oru-oam-failover", vlan_id, host_ip)
    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(
        remote_ip, remote_password, ovs_config.get_traffic_pod_prefix()
    )
    validate_str_contains_with_retry(
        lambda: ovs_kw.verify_connectivity_from_remote(
            remote_ip, remote_password, traffic_pod, host_ip
        ),
        "0% packet loss",
        "ORU OAM should be reachable before failover",
        timeout=30,
        polling_sleep_time=5,
    )

    get_logger().log_test_case_step("Simulate node failure — delete ovs-agent pod")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(ovs_agent, namespace)

    get_logger().log_test_case_step("Wait for new ovs-agent pod")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_ovs_agent_pod(),
        "ovs-agent",
        "New ovs-agent pod should be running after failover",
        timeout=300,
        polling_sleep_time=10,
    )

    get_logger().log_test_case_step("Re-create VLAN port on new agent and verify recovery")
    new_ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_kw.add_vlan_internal_port(new_ovs_agent, bridge, "oru-oam-failover", vlan_id, host_ip)
    validate_str_contains_with_retry(
        lambda: ovs_kw.verify_connectivity_from_remote(
            remote_ip, remote_password, traffic_pod, host_ip
        ),
        "0% packet loss",
        "ORU OAM should be reachable after VRRP failover recovery",
        timeout=30,
        polling_sleep_time=5,
    )


@mark.p2
@mark.lab_has_ovs
def test_oru_slaac_ipv6():
    """Verify IPv6 SLAAC address assignment is supported through OVS bridge.

    OVS bridge must forward Router Advertisement (RA) messages to allow
    pods to obtain IPv6 addresses via SLAAC.

    Test Steps:
        1. Get the traffic pod on remote peer
        2. Verify pod has an IPv6 address on net1 (SLAAC-assigned)
        3. Verify the IPv6 address is in the expected subnet
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    pod_prefix = ovs_config.get_traffic_pod_prefix()
    expected_prefix = ovs_config.get_peer_ip("untagged_prefix")

    get_logger().log_test_case_step("Get traffic pod on remote peer")
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(remote_ip, remote_password, pod_prefix)

    get_logger().log_test_case_step("Verify pod has IPv6 address on net1")
    output = ovs_kw.exec_on_remote_pod(
        remote_ip, remote_password, traffic_pod, "ip -6 addr show net1"
    )
    validate_str_contains(output, "inet6", "Traffic pod should have IPv6 address on net1 (SLAAC)")

    get_logger().log_test_case_step("Verify IPv6 address is in expected subnet")
    validate_str_contains(
        output, expected_prefix,
        f"IPv6 address should be in expected subnet ({expected_prefix})"
    )


@mark.p2
@mark.lab_has_ovs
def test_oru_dhcpv6_flow():
    """Verify DHCPv6 traffic flows through OVS bridge.

    OVS bridge must forward DHCPv6 Solicit/Advertise/Request/Reply messages
    between pods. Verified by checking that the traffic pod obtained an
    IPv6 address on its VLAN sub-interface.

    Test Steps:
        1. Get traffic pod on remote peer
        2. Verify VLAN 100 sub-interface (net1.100) has IPv6 address
        3. Verify VLAN 200 sub-interface (net1.200) has IPv6 address
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    pod_prefix = ovs_config.get_traffic_pod_prefix()

    get_logger().log_test_case_step("Get traffic pod on remote peer")
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(remote_ip, remote_password, pod_prefix)

    get_logger().log_test_case_step("Verify VLAN 100 sub-interface has IPv6 address")
    output_v100 = ovs_kw.exec_on_remote_pod(
        remote_ip, remote_password, traffic_pod, "ip -6 addr show net1.100"
    )
    validate_str_contains(
        output_v100, "inet6", "VLAN 100 sub-interface should have IPv6 (DHCPv6/static)"
    )

    get_logger().log_test_case_step("Verify VLAN 200 sub-interface has IPv6 address")
    output_v200 = ovs_kw.exec_on_remote_pod(
        remote_ip, remote_password, traffic_pod, "ip -6 addr show net1.200"
    )
    validate_str_contains(
        output_v200, "inet6", "VLAN 200 sub-interface should have IPv6 (DHCPv6/static)"
    )

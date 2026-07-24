"""Test OVS inter-server L2 forwarding.

Inter-server L2 forwarding tests validate traffic between two AIO-SX
systems connected via upstream switches. Traffic paths include untagged,
VLAN-tagged, and VRRP gateway scenarios.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p1
@mark.lab_has_ovs
def test_inter_server_l2_untagged():
    """Verify inter-server L2 forwarding on untagged traffic.

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge IP from remote peer pod (untagged)
        3. Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    target_ip = ovs_config.get_bridge_ip("untagged")

    get_logger().log_test_case_step("Get remote peer traffic pod")
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(remote_ip, remote_password, ovs_config.get_traffic_pod_prefix())

    get_logger().log_test_case_step("Ping bridge untagged IP from remote peer pod")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 5 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "Untagged L2 traffic should flow between servers")


@mark.p1
@mark.lab_has_ovs
def test_inter_server_l2_vlan100():
    """Verify inter-server L2 forwarding on VLAN 100.

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge VLAN 100 IP from remote peer pod
        3. Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    target_ip = ovs_config.get_bridge_ip("vlan100")

    get_logger().log_test_case_step("Get remote peer traffic pod")
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(remote_ip, remote_password, ovs_config.get_traffic_pod_prefix())

    get_logger().log_test_case_step("Ping bridge VLAN 100 IP from remote peer pod")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 5 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "VLAN 100 traffic should flow between servers")


@mark.p1
@mark.lab_has_ovs
def test_inter_server_l2_vlan200():
    """Verify inter-server L2 forwarding on VLAN 200.

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge VLAN 200 IP from remote peer pod
        3. Verify 0% packet loss
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    remote_ip = ovs_config.get_remote_peer_ip()
    remote_password = ovs_config.get_remote_peer_password()
    target_ip = ovs_config.get_bridge_ip("vlan200")

    get_logger().log_test_case_step("Get remote peer traffic pod")
    traffic_pod = ovs_kw.get_remote_pod_by_prefix(remote_ip, remote_password, ovs_config.get_traffic_pod_prefix())

    get_logger().log_test_case_step("Ping bridge VLAN 200 IP from remote peer pod")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 5 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "VLAN 200 traffic should flow between servers")


@mark.p1
@mark.lab_has_ovs
def test_inter_server_vrrp_gateway(request: FixtureRequest):
    """Verify VRRP gateway reachable via inter-server path.

    Test Steps:
        1. Create OVS internal port with VLAN tag for VRRP subnet
        2. Assign host IP in VRRP subnet
        3. Verify VRRP VIP is reachable from OVS bridge

    Teardown:
        - Remove the VLAN internal port from OVS bridge
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    vrrp_cfg = ovs_config.get_vrrp_config("vlan702")
    vip = vrrp_cfg.get("vip_v4", "")
    host_ip = vrrp_cfg.get("host_v4", "")
    vlan_name = "vlan702"
    vlan_id = "702"

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove VRRP VLAN internal port")
        ovs_kw.ovs_vsctl(ovs_agent, f"del-port {ovs_config.get_bridge_name()} {vlan_name}")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create OVS internal port with VLAN tag for VRRP subnet")
    ovs_kw.add_vlan_internal_port(ovs_agent, ovs_config.get_bridge_name(), vlan_name, int(vlan_id), host_ip)

    get_logger().log_test_case_step("Verify VRRP VIP is reachable from OVS bridge")
    output = ovs_kw.verify_connectivity(ovs_agent, vip)
    validate_str_contains(output, "reply", "VRRP VIP should be reachable from OVS bridge via inter-switch path")


@mark.p1
@mark.lab_has_ovs
def test_inter_server_bfd_vrrp_combined(request: FixtureRequest):
    """Verify combined BFD + VRRP scenario on fronthaul VLAN.

    Test Steps:
        1. Verify BFD is running on inter-server port
        2. Create OVS internal port with VLAN tag for fronthaul subnet
        3. Assign host IPv6 in fronthaul subnet
        4. Verify VRRP VIP is reachable (IPv6)

    Teardown:
        - Remove the VLAN internal port from OVS bridge
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    # VLAN IDs and VIPs are lab-specific, loaded from the 'vrrp' section
    # of the lab config file (e.g., vlan702, vlan707, vlan708 keys).
    vrrp_vlans = ovs_config.get_vrrp_config("fronthaul")
    if not vrrp_vlans:
        # Fallback: use first available VRRP config that has IPv6 VIP
        for key in ["vlan708", "vlan707", "vlan702"]:
            cfg = ovs_config.get_vrrp_config(key)
            if cfg.get("vip_v6"):
                vrrp_vlans = cfg
                vlan_name = key
                vlan_id = key.replace("vlan", "")
                break
    else:
        vlan_name = "fronthaul"
        vlan_id = str(vrrp_vlans.get("vlan_id", ""))

    vip_v6 = vrrp_vlans.get("vip_v6", "")
    host_v6 = vrrp_vlans.get("host_v6", "")

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove fronthaul VLAN internal port")
        ovs_kw.ovs_vsctl(ovs_agent, f"del-port {ovs_config.get_bridge_name()} {vlan_name}")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Verify BFD is active on inter-server port")
    bfd_status = ovs_kw.ovs_vsctl(ovs_agent, f"get interface {ovs_config.get_bfd_interfaces()[0]} bfd_status")
    validate_str_contains(bfd_status, "state=", "BFD should be active for combined scenario")

    get_logger().log_test_case_step("Create OVS internal port with VLAN tag for fronthaul")
    ovs_kw.add_vlan_internal_port(ovs_agent, ovs_config.get_bridge_name(), vlan_name, int(vlan_id), host_v6)

    get_logger().log_test_case_step("Verify VRRP VIP (IPv6) is reachable via BFD-tracked path")
    output = ovs_kw.verify_connectivity(ovs_agent, vip_v6)
    validate_str_contains(output, "reply", "Fronthaul VRRP VIP should be reachable via BFD-tracked inter-switch path")

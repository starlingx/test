"""Test OVS L2 forwarding.

L2 forwarding tests validate basic traffic flow through the OVS bridge
including untagged, VLAN-tagged, IPv6, and mixed scenarios.
"""

from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p1
@mark.lab_has_ovs
def test_l2_untagged_forwarding():
    """Verify L2 bridging of untagged IPv6 unicast traffic.

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge untagged IP from remote peer pod
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

    get_logger().log_test_case_step("Ping bridge untagged IP from remote peer")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 5 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "Untagged L2 traffic should be forwarded through OVS bridge")


@mark.p1
@mark.lab_has_ovs
def test_l2_vlan100_forwarding():
    """Verify L2 bridging of VLAN 100 tagged traffic.

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
    validate_str_contains(output, " 0% packet loss", "VLAN 100 traffic should be forwarded through OVS bridge")


@mark.p1
@mark.lab_has_ovs
def test_l2_ipv6_unicast():
    """Verify L2 bridging of IPv6 unicast traffic.

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge IP (IPv6) from remote peer
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

    get_logger().log_test_case_step("Ping bridge IPv6 address from remote peer")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 5 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "IPv6 unicast traffic should be forwarded")


@mark.p1
@mark.lab_has_ovs
def test_l2_vlan200_forwarding():
    """Verify L2 bridging on VLAN 200 (mixed tagged traffic).

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge VLAN 200 IP from remote peer
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

    get_logger().log_test_case_step("Ping bridge VLAN 200 IP from remote peer")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 5 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "VLAN 200 traffic should be forwarded")


@mark.p1
@mark.lab_has_ovs
def test_native_vlan_forwarding():
    """Verify native VLAN configuration on OVSPort.

    Test Steps:
        1. Get remote peer traffic pod
        2. Ping bridge IP using the native (untagged) path
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

    get_logger().log_test_case_step("Ping native VLAN IP from remote peer")
    output = ovs_kw.exec_on_remote_pod(remote_ip, remote_password, traffic_pod, f"ping6 -c 3 -W 2 {target_ip}")
    validate_str_contains(output, " 0% packet loss", "Native VLAN traffic should be forwarded correctly")

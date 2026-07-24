"""Test OVS VRRP gateway failover via switch-based VRRP.

VRRP tests verify gateway reachability through switch-based VRRP by
creating OVS internal ports with VLAN tags and verifying VIP connectivity.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains_with_retry
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


@mark.p1
@mark.lab_has_ovs
def test_vrrp_failover_vlan702(request: FixtureRequest):
    """Verify VRRP gateway reachability on management VLAN.

    Test Steps:
        1. Create OVS internal port with VLAN tag
        2. Assign host IP in VRRP subnet
        3. Verify VRRP VIP (IPv4) is reachable

    Teardown:
        - Remove VLAN internal port from OVS bridge
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    vrrp_cfg = ovs_config.get_vrrp_config("vlan702")
    vip_v4 = vrrp_cfg.get("vip_v4", "")
    host_v4 = vrrp_cfg.get("host_v4", "")

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove VLAN 702 internal port")
        ovs_kw.ovs_vsctl(ovs_agent, f"del-port {ovs_config.get_bridge_name()} vlan702")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Setup VLAN 702 internal port on OVS bridge")
    ovs_kw.add_vlan_internal_port(ovs_agent, ovs_config.get_bridge_name(), "vlan702", 702, host_v4)

    get_logger().log_test_case_step("Verify VRRP VIP is reachable on VLAN 702")
    validate_str_contains_with_retry(
        lambda: ovs_kw.verify_connectivity(ovs_agent, vip_v4),
        "reply",
        "VRRP VIP should be reachable on management VLAN",
        timeout=30,
        polling_sleep_time=5,
    )


@mark.p1
@mark.lab_has_ovs
def test_vrrp_failover_vlan707(request: FixtureRequest):
    """Verify VRRP gateway reachability on OAM VLAN.

    Test Steps:
        1. Create OVS internal port with VLAN 707 tag
        2. Assign host IP in VRRP subnet
        3. Verify VRRP VIP (IPv4) is reachable

    Teardown:
        - Remove VLAN internal port from OVS bridge
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    vrrp_cfg = ovs_config.get_vrrp_config("vlan707")
    vip_v4 = vrrp_cfg.get("vip_v4", "")
    host_v4 = vrrp_cfg.get("host_v4", "")

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove VLAN 707 internal port")
        ovs_kw.ovs_vsctl(ovs_agent, f"del-port {ovs_config.get_bridge_name()} vlan707")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Setup VLAN 707 internal port on OVS bridge")
    ovs_kw.add_vlan_internal_port(ovs_agent, ovs_config.get_bridge_name(), "vlan707", 707, host_v4)

    get_logger().log_test_case_step("Verify VRRP VIP is reachable on VLAN 707")
    validate_str_contains_with_retry(
        lambda: ovs_kw.verify_connectivity(ovs_agent, vip_v4),
        "reply",
        "VRRP VIP should be reachable on OAM VLAN",
        timeout=30,
        polling_sleep_time=5,
    )


@mark.p1
@mark.lab_has_ovs
def test_vrrp_failover_vlan708(request: FixtureRequest):
    """Verify VRRP gateway reachability on fronthaul VLAN.

    Test Steps:
        1. Create OVS internal port with VLAN 708 tag
        2. Assign host IP in VRRP subnet
        3. Verify VRRP VIP (IPv4) is reachable

    Teardown:
        - Remove VLAN internal port from OVS bridge
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()

    vrrp_cfg = ovs_config.get_vrrp_config("vlan708")
    vip_v4 = vrrp_cfg.get("vip_v4", "")
    host_v4 = vrrp_cfg.get("host_v4", "")

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove VLAN 708 internal port")
        ovs_kw.ovs_vsctl(ovs_agent, f"del-port {ovs_config.get_bridge_name()} vlan708")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Setup VLAN 708 internal port on OVS bridge")
    ovs_kw.add_vlan_internal_port(ovs_agent, ovs_config.get_bridge_name(), "vlan708", 708, host_v4)

    get_logger().log_test_case_step("Verify VRRP VIP is reachable on VLAN 708")
    validate_str_contains_with_retry(
        lambda: ovs_kw.verify_connectivity(ovs_agent, vip_v4),
        "reply",
        "VRRP VIP should be reachable on fronthaul VLAN",
        timeout=30,
        polling_sleep_time=5,
    )

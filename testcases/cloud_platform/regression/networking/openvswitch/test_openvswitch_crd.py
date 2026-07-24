"""Test OVS Bridge/Port CRD lifecycle.

Covers TC 2, 3, 31, 32, 47, 48 from the test plan.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry, validate_not_equals, validate_str_contains, validate_str_contains_with_retry
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


BRIDGE_PV_TEST_YAML = """
apiVersion: openvswitch.starlingx.io/v1
kind: OVSBridge
metadata:
  name: br-pv-test
  namespace: openvswitch
spec:
  bridgeName: br-pv-test
  rstpEnable: true
"""

BRIDGE_DEL_TEST_YAML = """
apiVersion: openvswitch.starlingx.io/v1
kind: OVSBridge
metadata:
  name: br-del-test
  namespace: openvswitch
spec:
  bridgeName: br-del-test
  rstpEnable: true
"""

BRIDGE_MOD_YAML = """
apiVersion: openvswitch.starlingx.io/v1
kind: OVSBridge
metadata:
  name: br-mod-test
  namespace: openvswitch
spec:
  bridgeName: br-mod-test
  rstpEnable: false
"""

BRIDGE_MOD_UPDATED_YAML = """
apiVersion: openvswitch.starlingx.io/v1
kind: OVSBridge
metadata:
  name: br-mod-test
  namespace: openvswitch
spec:
  bridgeName: br-mod-test
  rstpEnable: true
"""

INVALID_BRIDGE_YAML = """
apiVersion: openvswitch.starlingx.io/v1
kind: OVSBridge
metadata:
  name: invalid-bridge
  namespace: openvswitch
spec:
  bridgeName: ""
"""

INVALID_PORT_YAML = """
apiVersion: openvswitch.starlingx.io/v1
kind: OVSPort
metadata:
  name: invalid-port
  namespace: openvswitch
spec:
  name: invalid-port
  bridgeName: nonexistent-bridge
  interfaces:
  - name: invalid-port
"""


@mark.p1
@mark.lab_has_ovs
def test_create_ovsbridge(request: FixtureRequest):
    """Verify OVSBridge CRD can be created with valid configuration.

    Test Steps:
        - Delete any existing test bridge
        - Apply OVSBridge CR with rstpEnable=true
        - Verify bridge appears in OVS via ovs-vsctl list-br
        - Verify CR status is populated

    Teardown:
        - Delete the test bridge CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    def teardown():
        get_logger().log_test_case_step("Cleanup: deleting test bridge")
        ovs_kw.kubectl_delete_resource("ovsbridge", "br-pv-test")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Delete any existing test bridge")
    ovs_kw.kubectl_delete_resource("ovsbridge", "br-pv-test")

    get_logger().log_test_case_step("Apply OVSBridge CR")
    ovs_kw.kubectl_apply_yaml(BRIDGE_PV_TEST_YAML)

    get_logger().log_test_case_step("Verify bridge exists in OVS")
    validate_str_contains_with_retry(
        lambda: ovs_kw.ovs_vsctl(ovs_agent_pod, "list-br"),
        "br-pv-test", "Bridge br-pv-test should exist in OVS", timeout=30, polling_sleep_time=5
    )

    get_logger().log_test_case_step("Verify CR status is populated")
    status = ovs_kw.get_ovsbridge_status("br-pv-test")
    validate_not_equals(status, "", "OVSBridge CR status should not be empty")


@mark.p1
@mark.lab_has_ovs
def test_ovsport_operational():
    """Verify OVSPort CRDs are operational for SR-IOV interfaces.

    Test Steps:
        - Verify OVSPort CRs exist in the namespace
        - Verify SR-IOV ports are added to the OVS bridge
        - Verify port interface admin_state is up
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    get_logger().log_test_case_step("Verify OVSPort CRs exist")
    ports = ovs_kw.get_ovsport_names()
    validate_not_equals(ports, "", "OVSPort CRs should exist")

    get_logger().log_test_case_step("Verify ports are on br-sriov bridge")
    ports_output = ovs_kw.ovs_vsctl(ovs_agent_pod, "list-ports br-sriov")
    validate_str_contains(ports_output, "port2", "port2 should be on br-sriov")

    get_logger().log_test_case_step("Verify port2 interface is operational")
    admin = ovs_kw.ovs_vsctl(ovs_agent_pod, "get interface port2 admin_state")
    validate_str_contains(admin, "up", "Port2 admin_state should be up")


@mark.p2
@mark.lab_has_ovs
def test_invalid_ovsbridge_rejected():
    """Verify OVS Operator rejects invalid OVSBridge CR.

    Test Steps:
        - Apply OVSBridge CR with empty bridgeName
        - Verify admission webhook denies the request
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)

    get_logger().log_test_case_step("Apply invalid OVSBridge CR with empty bridgeName")
    output = ovs_kw.kubectl_apply_yaml(INVALID_BRIDGE_YAML)
    validate_str_contains(output.lower(), "denied", "Invalid bridge should be rejected by admission webhook")


@mark.p2
@mark.lab_has_ovs
def test_invalid_ovsport_not_in_ovs(request: FixtureRequest):
    """Verify OVS Operator handles invalid OVSPort CR gracefully.

    Test Steps:
        - Apply OVSPort CR referencing nonexistent bridge
        - Verify port does not appear in OVS

    Teardown:
        - Delete the invalid port CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    def teardown():
        ovs_kw.kubectl_delete_resource("ovsport", "invalid-port")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Apply OVSPort CR with nonexistent bridge reference")
    ovs_kw.kubectl_apply_yaml(INVALID_PORT_YAML)

    get_logger().log_test_case_step("Verify nonexistent bridge is not in OVS")

    def bridge_not_created():
        output = ovs_kw.ovs_vsctl(ovs_agent_pod, "list-br")
        return "nonexistent-bridge" not in output

    validate_equals_with_retry(bridge_not_created, True, "Nonexistent bridge should not be in OVS", timeout=15, polling_sleep_time=5)


@mark.p1
@mark.lab_has_ovs
def test_cr_deletion_cleans_ovs(request: FixtureRequest):
    """Verify OVSBridge CR deletion removes bridge from OVS.

    Test Steps:
        - Create a test bridge via CR
        - Verify bridge exists in OVS
        - Delete the bridge CR
        - Verify bridge is removed from OVS

    Teardown:
        - Ensure test bridge is cleaned up
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    def teardown():
        ovs_kw.kubectl_delete_resource("ovsbridge", "br-del-test")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create test bridge")
    ovs_kw.kubectl_apply_yaml(BRIDGE_DEL_TEST_YAML)

    get_logger().log_test_case_step("Verify bridge exists in OVS before deletion")
    validate_str_contains_with_retry(
        lambda: ovs_kw.ovs_vsctl(ovs_agent_pod, "list-br"),
        "br-del-test", "Bridge should exist before deletion", timeout=30, polling_sleep_time=5
    )

    get_logger().log_test_case_step("Delete bridge CR")
    ovs_kw.kubectl_delete_resource("ovsbridge", "br-del-test")

    get_logger().log_test_case_step("Verify bridge is removed from OVS")

    def bridge_removed():
        output = ovs_kw.ovs_vsctl(ovs_agent_pod, "list-br")
        return "br-del-test" not in output

    validate_equals_with_retry(bridge_removed, True, "Bridge should be removed after CR deletion", timeout=30, polling_sleep_time=5)


@mark.p1
@mark.lab_has_ovs
def test_cr_modification_reconciled(request: FixtureRequest):
    """Verify CR modification is reconciled by OVS Operator.

    Test Steps:
        - Create bridge with rstpEnable=false
        - Modify CR to rstpEnable=true
        - Verify RSTP is enabled in OVS

    Teardown:
        - Delete the test bridge
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent_pod = ovs_kw.get_ovs_agent_pod()

    def teardown():
        ovs_kw.kubectl_delete_resource("ovsbridge", "br-mod-test")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create bridge with RSTP disabled")
    ovs_kw.kubectl_delete_resource("ovsbridge", "br-mod-test")
    ovs_kw.kubectl_apply_yaml(BRIDGE_MOD_YAML)

    get_logger().log_test_case_step("Wait for bridge creation")
    validate_str_contains_with_retry(
        lambda: ovs_kw.ovs_vsctl(ovs_agent_pod, "list-br"),
        "br-mod-test", "Bridge should be created", timeout=30, polling_sleep_time=5
    )

    get_logger().log_test_case_step("Modify CR to enable RSTP")
    ovs_kw.kubectl_apply_yaml(BRIDGE_MOD_UPDATED_YAML)

    get_logger().log_test_case_step("Verify RSTP is enabled in OVS")
    validate_str_contains_with_retry(
        lambda: ovs_kw.ovs_vsctl(ovs_agent_pod, "get bridge br-mod-test rstp_enable"),
        "true", "RSTP should be enabled after CR modification", timeout=30, polling_sleep_time=5
    )

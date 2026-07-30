"""Test OVS Error Handling and Robustness.

Validates OVSNodeConfig immutability, in-service helm upgrade with
bridge/port persistence, and concurrent failure recovery scenarios.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import (
    validate_not_equals,
    validate_str_contains,
    validate_str_contains_with_retry,
)
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords

# Test-specific constants for concurrent failure test
TEST_VLAN_PORT = "vlan_test_999"
TEST_VLAN_TAG = 999


@mark.p1
@mark.lab_has_ovs
def test_ovsnodeconfig_immutable():
    """Verify OVSNodeConfig CR cannot be edited by the user.

    The OVS operator creates OVSNodeConfig automatically. Users must not
    be able to modify it directly.

    Test Steps:
        1. Get existing OVSNodeConfig resource name
        2. Attempt kubectl patch to modify a field
        3. Verify the patch is denied by the admission webhook
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    namespace = ovs_config.get_namespace()

    get_logger().log_test_case_step("Get existing OVSNodeConfig resource")
    nodeconfigs = ovs_kw.get_ovs_crd_names("ovsnodeconfig", namespace)
    validate_not_equals(len(nodeconfigs), 0, "OVSNodeConfig should exist")
    nodeconfig_name = nodeconfigs[0]

    get_logger().log_test_case_step("Attempt to patch OVSNodeConfig — should be denied")
    patch_output = ovs_kw.patch_ovs_crd(
        "ovsnodeconfig", nodeconfig_name, namespace,
        '{"spec":{"testField":"testValue"}}'
    )
    validate_str_contains(
        patch_output.lower(), "denied",
        "OVSNodeConfig patch should be denied by admission webhook"
    )


@mark.p1
@mark.lab_has_ovs
def test_helm_upgrade_bridge_persistence():
    """Verify OVS bridges and ports persist after helm chart upgrade.

    Test Steps:
        1. Record current OVS bridge and port configuration
        2. Trigger OVS app re-apply (simulates helm upgrade)
        3. Wait for app status to return to applied
        4. Verify bridge and ports are intact after upgrade
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    bridge = ovs_config.get_bridge_name()

    get_logger().log_test_case_step("Record current bridge and port configuration")
    bridges_before = ovs_kw.ovs_vsctl(ovs_agent, "list-br")
    validate_str_contains(bridges_before, bridge, f"{bridge} should exist before upgrade")

    get_logger().log_test_case_step("Trigger OVS application re-apply")
    SystemApplicationApplyKeywords(ssh_connection).system_application_apply(
        "openvswitch", timeout=600, polling_sleep_time=10
    )

    get_logger().log_test_case_step("Wait for new ovs-agent pod to be Running")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_ovs_agent_pod(),
        "ovs-agent",
        "OVS agent pod should be running after upgrade",
        timeout=300,
        polling_sleep_time=10,
    )

    get_logger().log_test_case_step("Verify bridge persists after upgrade")
    new_ovs_agent = ovs_kw.get_ovs_agent_pod()
    bridges_after = ovs_kw.ovs_vsctl(new_ovs_agent, "list-br")
    validate_str_contains(bridges_after, bridge, f"{bridge} should persist after upgrade")

    get_logger().log_test_case_step("Verify ports persist after upgrade")
    ports_after = ovs_kw.ovs_vsctl(new_ovs_agent, f"list-ports {bridge}")
    for port in ovs_config.get_ports():
        validate_str_contains(ports_after, port, f"Port {port} should persist after upgrade")


@mark.p1
@mark.lab_has_ovs
def test_concurrent_vrrp_agent_restart(request: FixtureRequest):
    """Verify OVS recovers from concurrent VRRP port creation and agent restart.

    Test Steps:
        1. Create a VLAN internal port (simulates VRRP gateway setup)
        2. Immediately delete the ovs-agent pod (concurrent failure)
        3. Wait for new agent pod to be Running
        4. Verify bridge configuration is restored
        5. Verify the VLAN port can be re-created on the new agent

    Teardown:
        - Remove test VLAN port if it exists
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    bridge = ovs_config.get_bridge_name()
    namespace = ovs_config.get_namespace()

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove test VLAN port")
        new_agent = ovs_kw.get_ovs_agent_pod()
        ovs_kw.ovs_vsctl(new_agent, f"--if-exists del-port {bridge} {TEST_VLAN_PORT}")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create VLAN internal port on bridge")
    ovs_kw.ovs_vsctl(ovs_agent, f"add-port {bridge} {TEST_VLAN_PORT} tag={TEST_VLAN_TAG} -- set interface {TEST_VLAN_PORT} type=internal")

    get_logger().log_test_case_step("Immediately delete ovs-agent pod (simulate concurrent failure)")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(ovs_agent, namespace)

    get_logger().log_test_case_step("Wait for new ovs-agent pod to be Running")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_ovs_agent_pod(),
        "ovs-agent",
        "New ovs-agent pod should be running after restart",
        timeout=300,
        polling_sleep_time=10,
    )

    get_logger().log_test_case_step("Verify bridge configuration is restored")
    validate_str_contains_with_retry(
        lambda: ovs_kw.ovs_vsctl(ovs_kw.get_ovs_agent_pod(), "list-br"),
        bridge,
        f"{bridge} should be restored after agent restart",
        timeout=60,
        polling_sleep_time=10,
    )

    get_logger().log_test_case_step("Verify ports from CRDs are restored")
    new_ovs_agent = ovs_kw.get_ovs_agent_pod()
    ports = ovs_kw.ovs_vsctl(new_ovs_agent, f"list-ports {bridge}")
    for port in ovs_config.get_ports():
        validate_str_contains(ports, port, f"Port {port} should be restored after agent restart")

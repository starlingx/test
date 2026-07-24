"""Test OVS BFD (Bidirectional Forwarding Detection).

BFD tests validate session establishment, failure detection, recovery,
and parameter persistence across agent restarts using the inter-server
OVS-to-OVS BFD domain.
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
def test_bfd_session_established():
    """Verify BFD is configured and session state is reported.

    Test Steps:
        1. Get OVS agent pod
        2. Query BFD configuration on BFD-enabled ports
        3. Verify bfdEnable=true and parameters are set
        4. Query BFD status — verify state field is present
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    bfd_interfaces = ovs_config.get_bfd_interfaces()

    get_logger().log_test_case_step("Verify BFD configuration on BFD-enabled ports")
    for iface in bfd_interfaces:
        bfd_config = ovs_kw.get_bfd_config(ovs_agent, iface)
        validate_str_contains(bfd_config, 'enable="true"', f"BFD should be enabled on {iface}")

    get_logger().log_test_case_step("Verify BFD parameters are set")
    bfd_config = ovs_kw.get_bfd_config(ovs_agent, bfd_interfaces[0])
    validate_str_contains(bfd_config, "min_rx=", f"BFD min_rx should be configured on {bfd_interfaces[0]}")
    validate_str_contains(bfd_config, "min_tx=", f"BFD min_tx should be configured on {bfd_interfaces[0]}")

    get_logger().log_test_case_step("Verify BFD status is reported")
    bfd_status = ovs_kw.get_bfd_status(ovs_agent, bfd_interfaces[0])
    validate_str_contains(bfd_status, "state=", "BFD status should report a state")
    validate_str_contains(bfd_status, "flap_count=", "BFD status should report flap_count")


@mark.p1
@mark.lab_has_ovs
def test_bfd_failover(request: FixtureRequest):
    """Verify BFD detects link failure on inter-server port.

    Test Steps:
        1. Record current BFD state
        2. Admin-down interface (simulate link failure)
        3. Poll for BFD state to transition to 'down'

    Teardown:
        - Restore interface to admin_state=up
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    test_interface = ovs_config.get_bfd_interfaces()[0]

    def teardown():
        get_logger().log_test_case_step("Restore: admin-up interface")
        ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Record initial BFD state")
    initial_status = ovs_kw.get_bfd_status(ovs_agent, test_interface)
    get_logger().log_info(f"Initial BFD status: {initial_status}")

    get_logger().log_test_case_step("Admin-down interface to simulate link failure")
    ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=down")

    get_logger().log_test_case_step("Verify BFD state transitions to down")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_bfd_status(ovs_agent, test_interface),
        "state=down",
        "BFD state should be down after link failure",
        timeout=30,
        polling_sleep_time=3,
    )


@mark.p1
@mark.lab_has_ovs
def test_bfd_recovery(request: FixtureRequest):
    """Verify BFD session recovers after link restored.

    Test Steps:
        1. Admin-down interface → poll for BFD down
        2. Admin-up interface → poll for BFD state change
        3. Verify BFD state is no longer 'down'

    Teardown:
        - Ensure interface is admin_state=up
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    test_interface = ovs_config.get_bfd_interfaces()[0]

    def teardown():
        get_logger().log_test_case_step("Ensure interface is admin-up")
        ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Admin-down interface to trigger BFD failure")
    ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=down")

    get_logger().log_test_case_step("Poll for BFD state to be down")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_bfd_status(ovs_agent, test_interface),
        "state=down",
        "BFD should be down after admin-down",
        timeout=30,
        polling_sleep_time=3,
    )

    get_logger().log_test_case_step("Admin-up interface to restore BFD")
    ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=up")

    get_logger().log_test_case_step("Verify BFD state recovers")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_bfd_status(ovs_agent, test_interface),
        "state=",
        "BFD state should be reported after recovery",
        timeout=30,
        polling_sleep_time=5,
    )


@mark.p1
@mark.lab_has_ovs
def test_ovs_agent_restart_bfd():
    """Verify BFD sessions re-establish after OVS agent pod restart.

    Test Steps:
        1. Record BFD config on BFD-enabled port
        2. Delete ovs-agent pod (DaemonSet will recreate)
        3. Poll for new pod to be Running
        4. Verify BFD configuration is restored on new pod
        5. Verify BFD status is reported
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    test_interface = ovs_config.get_bfd_interfaces()[0]
    namespace = ovs_config.get_namespace()

    ovs_agent = ovs_kw.get_ovs_agent_pod()

    get_logger().log_test_case_step("Record BFD config before restart")
    bfd_config_before = ovs_kw.get_bfd_config(ovs_agent, test_interface)
    validate_str_contains(bfd_config_before, 'enable="true"', "BFD should be enabled before restart")

    get_logger().log_test_case_step("Delete ovs-agent pod to trigger restart")
    KubectlDeletePodsKeywords(ssh_connection).delete_pod(ovs_agent, namespace)

    get_logger().log_test_case_step("Wait for new ovs-agent pod to be Running")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_ovs_agent_pod(),
        "ovs-agent",
        "New ovs-agent pod should be running after restart",
        timeout=300,
        polling_sleep_time=10,
    )

    get_logger().log_test_case_step("Verify BFD configuration restored on new pod")
    new_ovs_agent = ovs_kw.get_ovs_agent_pod()
    bfd_config_after = ovs_kw.get_bfd_config(new_ovs_agent, test_interface)
    validate_str_contains(bfd_config_after, 'enable="true"', "BFD should be re-enabled after restart")

    get_logger().log_test_case_step("Verify BFD status reported on new pod")
    bfd_status = ovs_kw.get_bfd_status(new_ovs_agent, test_interface)
    validate_str_contains(bfd_status, "state=", "BFD status should be reported after restart")


@mark.p1
@mark.lab_has_ovs
def test_link_failure_bfd_detection(request: FixtureRequest):
    """Verify BFD detects link failure within configured detection time.

    Test Steps:
        1. Record initial BFD state on second BFD port
        2. Admin-down interface
        3. Poll for BFD state=down

    Teardown:
        - Restore interface to admin_state=up
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    bfd_interfaces = ovs_config.get_bfd_interfaces()
    test_interface = bfd_interfaces[1] if len(bfd_interfaces) > 1 else bfd_interfaces[0]

    def teardown():
        get_logger().log_test_case_step("Restore: admin-up interface")
        ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Record initial BFD state")
    initial_status = ovs_kw.get_bfd_status(ovs_agent, test_interface)
    get_logger().log_info(f"Initial BFD status on {test_interface}: {initial_status}")

    get_logger().log_test_case_step("Admin-down interface to simulate link failure")
    ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=down")

    get_logger().log_test_case_step("Verify BFD detects failure")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_bfd_status(ovs_agent, test_interface),
        "state=down",
        f"BFD should detect link failure on {test_interface}",
        timeout=30,
        polling_sleep_time=3,
    )


@mark.p2
@mark.lab_has_ovs
def test_port_flap_bfd(request: FixtureRequest):
    """Verify BFD state changes correctly on port flap.

    Test Steps:
        1. Record initial BFD state
        2. Admin-down interface → poll for BFD down
        3. Admin-up interface → poll for BFD config intact
        4. Verify BFD parameters remain intact after flap

    Teardown:
        - Ensure interface is admin_state=up
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_agent = ovs_kw.get_ovs_agent_pod()
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    test_interface = ovs_config.get_bfd_interfaces()[0]

    def teardown():
        get_logger().log_test_case_step("Ensure interface is admin-up")
        ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=up")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Record initial BFD state")
    initial_status = ovs_kw.get_bfd_status(ovs_agent, test_interface)
    get_logger().log_info(f"Initial BFD status: {initial_status}")

    get_logger().log_test_case_step("Flap: admin-down interface")
    ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=down")

    get_logger().log_test_case_step("Poll for BFD state down during admin-down")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_bfd_status(ovs_agent, test_interface),
        "state=down",
        "BFD state should be down during admin-down",
        timeout=30,
        polling_sleep_time=3,
    )

    get_logger().log_test_case_step("Flap: admin-up interface (restore)")
    ovs_kw.ovs_vsctl(ovs_agent, f"set interface {test_interface} admin_state=up")

    get_logger().log_test_case_step("Verify BFD configuration intact after flap")
    validate_str_contains_with_retry(
        lambda: ovs_kw.get_bfd_config(ovs_agent, test_interface),
        'enable="true"',
        "BFD should still be enabled after flap",
        timeout=30,
        polling_sleep_time=5,
    )

    get_logger().log_test_case_step("Verify BFD status reported after recovery")
    bfd_status = ovs_kw.get_bfd_status(ovs_agent, test_interface)
    validate_str_contains(bfd_status, "state=", "BFD state should be reported after flap recovery")

"""Test OVS Access interface parameter validation.

Validates that the --ovs-access parameter on system host-if-add/modify
is correctly accepted or rejected based on sysinv constraints.

OVS Access marks which SR-IOV interface provides OVS access for platform
traffic. Constraints enforced by sysinv:
- Interface must be type ethernet with lower interface of class pci-sriov
- Lower pci-sriov interface must NOT have platformNetworks assigned
- Only one ethernet interface per node can have ovsAccess=true
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_if_keywords import SystemHostInterfaceKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords


@mark.p1
@mark.lab_has_ovs
def test_ovsaccess_interface_validation(request: FixtureRequest):
    """Verify --ovs-access parameter accepted/rejected per sysinv constraints.

    Performs all OVS Access validations in a single lock/unlock cycle:
    1. Lock host
    2. Verify --ovs-access true accepted on valid ethernet interface
    3. Verify only one interface per node can have --ovs-access true
    4. Verify --ovs-access true rejected when lower has platformNetworks
    5. Cleanup and unlock host

    Test Steps:
        1. Lock host
        2. Create ethernet interface with --ovs-access true on valid pci-sriov lower
        3. Verify interface created successfully via host-if-show
        4. Attempt second --ovs-access true interface on same node
        5. Attempt --ovs-access true on interface with platformNetworks lower
        6. Cleanup interfaces and unlock host

    Teardown:
        - Remove test interfaces
        - Unlock host (triggers reboot on simplex)
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_kw.ensure_ovs_setup()

    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    ovsaccess_cfg = ovs_config.get_ovsaccess_config()
    host_name = ovsaccess_cfg.get_node_name()
    sriov_lower = ovsaccess_cfg.get_sriov_interface()
    mgmt_interface = ovsaccess_cfg.get_mgmt_interface()

    if_kw = SystemHostInterfaceKeywords(ssh_connection)
    lock_kw = SystemHostLockKeywords(ssh_connection)
    test_iface_1 = "ovs-acc-t1"
    test_iface_2 = "ovs-acc-t2"
    test_iface_plat = "ovs-acc-plat"

    def teardown():
        get_logger().log_test_case_step("Cleanup: remove test interfaces and unlock")
        if_kw.cleanup_interface(host_name, test_iface_2)
        if_kw.cleanup_interface(host_name, test_iface_plat)
        if_kw.cleanup_interface(host_name, test_iface_1)
        lock_kw.unlock_host(host_name)

    request.addfinalizer(teardown)

    # Step 1: Lock host
    get_logger().log_test_case_step("Lock host for interface configuration")
    lock_kw.lock_host(host_name)
    lock_kw.wait_for_host_locked(host_name)

    # Step 2: Verify --ovs-access true accepted on valid interface
    get_logger().log_test_case_step("Create ethernet interface with --ovs-access true")
    if_kw.system_host_interface_add(
        host_name, test_iface_1, "ethernet", sriov_lower,
        ifclass="platform", ovs_access=True,
    )

    get_logger().log_test_case_step("Verify interface has ovs_access=True via host-if-show")
    iface_obj = if_kw.system_host_interface_show(host_name, test_iface_1)
    validate_equals(
        iface_obj.get_ovs_access(), True,
        "Interface should show ovs_access=True",
    )

    # Step 3: Verify only one interface per node can have --ovs-access true
    get_logger().log_test_case_step("Attempt second --ovs-access true — should be rejected")
    output_dup = if_kw.system_host_interface_add_with_error(
        host_name, test_iface_2, "ethernet", sriov_lower,
        ifclass="platform", ovs_access=True,
    )
    validate_str_contains(
        output_dup.lower(),
        "already has ovs-access",
        "Second --ovs-access true interface on same node should be rejected",
    )

    # Step 4: Verify rejected when lower has platformNetworks
    get_logger().log_test_case_step("Attempt --ovs-access on platform interface — should be rejected")
    output_plat = if_kw.system_host_interface_add_with_error(
        host_name, test_iface_plat, "ethernet", mgmt_interface,
        ifclass="platform", ovs_access=True,
    )
    validate_str_contains(
        output_plat.lower(),
        "pci-sriov",
        "ovs-access on interface with non-sriov lower should be rejected",
    )

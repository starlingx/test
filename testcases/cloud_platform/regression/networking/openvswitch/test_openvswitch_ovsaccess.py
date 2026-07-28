"""Test OVSAccess CR validation.

Validates that the OVSAccess Custom Resource is correctly accepted or
rejected based on deployment-manager constraints. OVSAccess defines
which platform interfaces can be used by the openvswitch application.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.networking.openvswitch.openvswitch_keywords import OpenvSwitchKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords


def _build_ovsaccess_yaml(name: str, interfaces: list[dict], platform_networks: list[str] | None = None) -> str:
    """Build OVSAccess CR YAML from config-driven parameters.

    Args:
        name: CR metadata name.
        interfaces: List of dicts with 'name' and 'node' keys.
        platform_networks: Optional list of platform network names.

    Returns:
        str: YAML manifest string.
    """
    iface_lines = ""
    for iface in interfaces:
        iface_lines += f"\n  - name: {iface['name']}\n    node: {iface['node']}"
        if platform_networks:
            iface_lines += "\n    platformNetworks:"
            for net in platform_networks:
                iface_lines += f"\n    - {net}"

    return (
        "apiVersion: openvswitch.starlingx.io/v1\n"
        "kind: OVSAccess\n"
        "metadata:\n"
        f"  name: {name}\n"
        "  namespace: openvswitch\n"
        "spec:\n"
        f"  interfaces:{iface_lines}\n"
    )


@mark.p1
@mark.lab_has_ovs
def test_ovsaccess_accepted(request: FixtureRequest):
    """Verify valid OVSAccess CR is accepted.

    Test Steps:
        1. Apply OVSAccess CR with valid single interface per node
        2. Verify CR is accepted (no error in output)
        3. Verify OVSAccess resource exists in namespace

    Teardown:
        - Delete the test OVSAccess CR
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    namespace = ovs_config.get_namespace()
    ovsaccess_cfg = ovs_config.get_ovsaccess_config()

    cr_name = "ovsaccess-valid-test"
    interface_name = ovsaccess_cfg.get_interface_name()
    node_name = ovsaccess_cfg.get_node_name()

    yaml_content = _build_ovsaccess_yaml(
        cr_name, [{"name": interface_name, "node": node_name}]
    )

    def teardown():
        get_logger().log_test_case_step("Cleanup: delete test OVSAccess CR")
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("ovsaccess", cr_name, namespace)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Apply valid OVSAccess CR")
    output = ovs_kw.kubectl_apply_yaml(yaml_content)
    validate_str_contains(
        output.lower(), "created",
        "Valid OVSAccess CR should be accepted"
    )

    get_logger().log_test_case_step("Verify OVSAccess resource exists")
    resources = ovs_kw.kubectl_get_resource("ovsaccess", namespace)
    validate_str_contains(
        resources, cr_name,
        "OVSAccess CR should be listed in namespace"
    )


@mark.p1
@mark.lab_has_ovs
def test_ovsaccess_rejected_platform_networks(request: FixtureRequest):
    """Verify OVSAccess CR is rejected when platformNetworks is specified.

    OVSAccess must not allow interfaces already assigned to platform
    networks (mgmt, oam). The admission webhook should deny the request.

    Test Steps:
        1. Apply OVSAccess CR with platformNetworks field
        2. Verify the CR is denied by the admission webhook

    Teardown:
        - Delete the test CR if it was accidentally created
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    namespace = ovs_config.get_namespace()
    ovsaccess_cfg = ovs_config.get_ovsaccess_config()

    cr_name = "ovsaccess-platform-test"
    interface_name = ovsaccess_cfg.get_interface_name()
    node_name = ovsaccess_cfg.get_node_name()

    yaml_content = _build_ovsaccess_yaml(
        cr_name,
        [{"name": interface_name, "node": node_name}],
        platform_networks=["mgmt", "oam"],
    )

    def teardown():
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("ovsaccess", cr_name, namespace)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Apply OVSAccess CR with platformNetworks — should be rejected")
    output = ovs_kw.kubectl_apply_yaml(yaml_content)
    validate_str_contains(
        output.lower(), "denied",
        "OVSAccess with platformNetworks should be denied by admission webhook"
    )


@mark.p2
@mark.lab_has_ovs
def test_ovsaccess_single_interface_per_node(request: FixtureRequest):
    """Verify OVSAccess rejects duplicate interfaces on the same node.

    Each interface should only be listed once per node in OVSAccess.

    Test Steps:
        1. Apply OVSAccess CR with duplicate interface entries
        2. Verify the CR is denied or reports an error

    Teardown:
        - Delete the test CR if it was accidentally created
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    ovs_kw = OpenvSwitchKeywords(ssh_connection)
    ovs_config = ConfigurationManager.get_lab_config().get_ovs_config()
    namespace = ovs_config.get_namespace()
    ovsaccess_cfg = ovs_config.get_ovsaccess_config()

    cr_name = "ovsaccess-duplicate-test"
    interface_name = ovsaccess_cfg.get_interface_name()
    node_name = ovsaccess_cfg.get_node_name()

    yaml_content = _build_ovsaccess_yaml(
        cr_name,
        [
            {"name": interface_name, "node": node_name},
            {"name": interface_name, "node": node_name},
        ],
    )

    def teardown():
        KubectlDeleteResourceKeywords(ssh_connection).delete_resource("ovsaccess", cr_name, namespace)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Apply OVSAccess CR with duplicate interface — should be rejected")
    output = ovs_kw.kubectl_apply_yaml(yaml_content)
    validate_str_contains(
        output.lower(), "denied",
        "OVSAccess with duplicate interface per node should be denied"
    )

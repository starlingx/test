"""Test suite for the openvswitch platform application.

Covers lifecycle (upload, apply, remove, delete), helm overrides,
chart attributes, OVS config overrides, HA pod recovery,
CRD registration, and OVSBridge CRD operations.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry, validate_not_equals, validate_str_contains
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_delete_input import SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_remove_input import SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.object.system_application_upload_input import SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import SystemApplicationDeleteKeywords
from keywords.cloud_platform.system.application.system_application_list_keywords import SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import SystemApplicationUploadKeywords
from keywords.cloud_platform.system.helm.system_helm_chart_attribute_modify_keywords import SystemHelmChartAttributeModifyKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.cloud_platform.system.host.system_host_list_keywords import SystemHostListKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.host.system_host_swact_keywords import SystemHostSwactKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.k8s.crd.kubectl_get_crd_keywords import KubectlGetCrdKeywords
from keywords.k8s.delete_resource.kubectl_delete_resource_keywords import KubectlDeleteResourceKeywords
from keywords.k8s.files.kubectl_file_apply_keywords import KubectlFileApplyKeywords
from keywords.k8s.lease.kubectl_get_lease_keywords import KubectlGetLeaseKeywords
from keywords.k8s.node.kubectl_label_node_keywords import KubectlLabelNodeKeywords
from keywords.k8s.pods.kubectl_delete_pods_keywords import KubectlDeletePodsKeywords
from keywords.k8s.pods.kubectl_exec_in_pods_keywords import KubectlExecInPodsKeywords
from keywords.k8s.pods.kubectl_get_pods_keywords import KubectlGetPodsKeywords

APP_NAME = "openvswitch"
APP_NAMESPACE = "openvswitch"
OVS_AGENT_CHART = "ovs-agent"
OVS_MANAGER_CHART = "ovs-manager"
BASE_APPLICATION_PATH = "/usr/local/share/applications/helm/"

OVS_EXPECTED_CRDS = [
    "ovsbridges.openvswitch.starlingx.io",
    "ovsports.openvswitch.starlingx.io",
    "ovsnodeconfigs.openvswitch.starlingx.io",
]

OVS_BRIDGE_NAME = "test-br0"
OVS_BRIDGE_YAML_DIR = "/home/sysadmin/test_openvswitch_app/test_files"
OVS_BRIDGE_YAML_PATH = f"{OVS_BRIDGE_YAML_DIR}/test-br0.yaml"
OVS_BRIDGE_YAML = """apiVersion: openvswitch.starlingx.io/v1
kind: OVSBridge
metadata:
  name: test-br0
  namespace: openvswitch
spec:
  bridgeName: test-br0
"""


def setup(request: FixtureRequest, active_ssh_connection: SSHConnection) -> str:
    """
    Setup function to ensure openvswitch is applied before tests.

    Args:
        request (FixtureRequest): pytest request fixture for teardown registration.
        active_ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The openvswitch application name.
    """
    app_list_kw = SystemApplicationListKeywords(active_ssh_connection)

    if not app_list_kw.is_app_present(APP_NAME):
        get_logger().log_setup_step("Upload openvswitch app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(APP_NAME)
        system_application_upload_input.set_tar_file_path(f"{BASE_APPLICATION_PATH}{APP_NAME}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

    app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(APP_NAME)
    current_status = app_show.get_system_application_object().get_status()

    if current_status not in ("applied", "uploaded"):
        get_logger().log_setup_step(f"App in bad state: {current_status}. Cleaning up.")
        SystemApplicationRemoveKeywords(active_ssh_connection).cleanup_app_if_present(app_name=APP_NAME, force_removal=True, force_deletion=True, timeout_in_seconds=300)
        get_logger().log_setup_step("Re-upload openvswitch app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(APP_NAME)
        system_application_upload_input.set_tar_file_path(f"{BASE_APPLICATION_PATH}{APP_NAME}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
        current_status = "uploaded"

    if current_status != "applied":
        get_logger().log_setup_step("Apply openvswitch app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=APP_NAME, timeout=600)

    get_logger().log_setup_step("Ensure nodes are labeled for OVS agent scheduling.")
    label_keywords = KubectlLabelNodeKeywords(active_ssh_connection)
    host_list = SystemHostListKeywords(active_ssh_connection).get_system_host_list().get_hosts()
    for host in host_list:
        label_keywords.label_node(host.get_host_name(), "ovs-node", "enabled")

    return APP_NAME


@mark.p2
def test_remove_apply_openvswitch_app(request: FixtureRequest):
    """
    Remove and apply the openvswitch application.

    Test Steps:
        - Run this command "system application-remove openvswitch"
        - The status of the application should change to uploaded
        - Run this command "system application-apply openvswitch"
        - The openvswitch application was applied

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)

    get_logger().log_test_case_step("Remove openvswitch")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(openvswitch_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Apply openvswitch")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=openvswitch_name)


@mark.p2
def test_delete_openvswitch_app(request: FixtureRequest):
    """
    Delete openvswitch application.

    Test Steps:
        - Run this command "system application-remove openvswitch"
        - The status of the application should change to uploaded
        - Run this command "system application-delete"
        - The openvswitch application was deleted

    Teardown:
        - Re-upload and apply openvswitch application

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Re-upload openvswitch")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(openvswitch_name)
        system_application_upload_input.set_tar_file_path(f"{BASE_APPLICATION_PATH}{openvswitch_name}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
        get_logger().log_teardown_step("Apply openvswitch")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=openvswitch_name, timeout=600)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Remove openvswitch")
    system_application_remove_input = SystemApplicationRemoveInput()
    system_application_remove_input.set_app_name(openvswitch_name)
    SystemApplicationRemoveKeywords(active_ssh_connection).system_application_remove(system_application_remove_input)

    get_logger().log_test_case_step("Delete openvswitch")
    system_application_delete_input = SystemApplicationDeleteInput()
    system_application_delete_input.set_app_name(openvswitch_name)
    app_delete_response = SystemApplicationDeleteKeywords(active_ssh_connection).get_system_application_delete(system_application_delete_input)
    validate_str_contains(app_delete_response.rstrip(), "deleted", "Application deletion.")


@mark.p2
def test_verify_helm_releases_openvswitch(request: FixtureRequest):
    """
    Verify helm releases visible via kubectl HelmRelease.

    Test Steps:
        - Verify ovs-agent HelmRelease exists and is Ready
        - Verify ovs-manager HelmRelease exists and is Ready

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    get_logger().log_test_case_step("Verify ovs-agent HelmRelease exists")
    ovs_agent_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, OVS_AGENT_CHART, APP_NAMESPACE)
    validate_not_equals(ovs_agent_show, None, "ovs-agent helm override exists")

    get_logger().log_test_case_step("Verify ovs-manager HelmRelease exists")
    ovs_manager_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, OVS_MANAGER_CHART, APP_NAMESPACE)
    validate_not_equals(ovs_manager_show, None, "ovs-manager helm override exists")


@mark.p2
def test_ovs_agent_containers_running(request: FixtureRequest):
    """
    Verify OVS agent pod has 3 containers running.

    Test Steps:
        - Get ovs-agent pod in openvswitch namespace
        - Verify pod has 3/3 containers in Running state

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    get_logger().log_test_case_step("Get ovs-agent pod")
    pods_output = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator")
    agent_pods = pods_output.get_pods()
    validate_not_equals(len(agent_pods), 0, "OVS agent pod exists")

    get_logger().log_test_case_step("Verify pod has 3/3 containers Running")
    agent_pod = agent_pods[0]
    validate_equals(agent_pod.get_status(), "Running", "OVS agent pod is Running")
    validate_str_contains(agent_pod.get_ready(), "3/3", "OVS agent pod has 3 containers ready")


@mark.p2
def test_ovs_crds_registered(request: FixtureRequest):
    """
    Verify OVS CRDs are registered after application apply.

    Test Steps:
        - Get list of CRDs
        - Verify ovsbridges CRD exists
        - Verify ovsports CRD exists
        - Verify ovsnodeconfigs CRD exists

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    crd_names = KubectlGetCrdKeywords(active_ssh_connection).get_crds().get_crd_names()
    for crd in OVS_EXPECTED_CRDS:
        get_logger().log_test_case_step(f"Verify {crd} CRD exists")
        validate_equals(crd in crd_names, True, f"CRD {crd} should be registered")


@mark.p2
def test_update_helm_chart_user_overrides_openvswitch(request: FixtureRequest):
    """
    Update helm chart user overrides for openvswitch application.

    Test Steps:
        - Show initial helm override properties and values
        - Set user_overrides testKey to testValue
        - Verify the update was applied correctly

    Teardown:
        - Delete the helm override
        - Verify override was deleted

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    chart_name = OVS_AGENT_CHART
    namespace = APP_NAMESPACE

    def teardown():
        get_logger().log_teardown_step("Delete helm override")
        helm_override_keywords.delete_system_helm_override(openvswitch_name, chart_name, namespace)

        get_logger().log_teardown_step("Verify helm override was deleted")
        final_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
        final_user_overrides = final_override_show.get_helm_override_show().get_user_overrides()
        validate_equals(final_user_overrides, "None", "User overrides should be None after deletion")

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    initial_user_overrides = initial_override_show.get_helm_override_show().get_user_overrides()
    get_logger().log_info(f"Initial user overrides: {initial_user_overrides}")

    get_logger().log_test_case_step("Set user_overrides testKey to testValue")
    override_values = "testKey=testValue"
    helm_override_keywords.update_helm_override_via_set(override_values, openvswitch_name, chart_name, namespace)

    get_logger().log_test_case_step("Verify the update was applied correctly")
    updated_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    updated_user_overrides = updated_override_show.get_helm_override_show().get_user_overrides()
    validate_str_contains(updated_user_overrides, "testValue", "User overrides should contain testValue")
    get_logger().log_info(f"Updated user overrides: {updated_user_overrides}")


@mark.p2
def test_delete_helm_chart_user_overrides_openvswitch(request: FixtureRequest):
    """
    Delete helm chart user overrides for openvswitch application.

    Test Steps:
        - Show initial helm override properties and values
        - Set user_overrides testKey to testValue
        - Delete the user-overrides configuration
        - Verify the delete was successful

    Teardown:
        - Delete helm override if still present

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)

    chart_name = OVS_AGENT_CHART
    namespace = APP_NAMESPACE

    def teardown():
        get_logger().log_teardown_step("Check and delete helm override if needed")
        current_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
        current_user_overrides = current_override_show.get_helm_override_show().get_user_overrides()
        if current_user_overrides != "None":
            helm_override_keywords.delete_system_helm_override(openvswitch_name, chart_name, namespace)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    get_logger().log_info(f"Initial user overrides: {initial_override_show.get_helm_override_show().get_user_overrides()}")

    get_logger().log_test_case_step("Set user_overrides testKey to testValue")
    override_values = "testKey=testValue"
    helm_override_keywords.update_helm_override_via_set(override_values, openvswitch_name, chart_name, namespace)

    get_logger().log_test_case_step("Delete the user-overrides configuration")
    helm_override_keywords.delete_system_helm_override(openvswitch_name, chart_name, namespace)

    get_logger().log_test_case_step("Verify the delete was successful")
    final_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    final_user_overrides = final_override_show.get_helm_override_show().get_user_overrides()
    validate_equals(final_user_overrides, "None", "User overrides should be None after deletion")
    get_logger().log_info(f"Final user overrides: {final_user_overrides}")


@mark.p2
def test_modify_helm_chart_attribute_openvswitch(request: FixtureRequest):
    """
    Modify helm chart attribute for openvswitch application.

    Test Steps:
        - Show initial helm override properties and values
        - Set the enabled parameter to false
        - Verify it was disabled
        - Set the enabled parameter to true
        - Verify it was enabled

    Teardown:
        - Set enabled attribute back to true

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)
    helm_override_keywords = SystemHelmOverrideKeywords(active_ssh_connection)
    helm_attribute_keywords = SystemHelmChartAttributeModifyKeywords(active_ssh_connection)

    chart_name = OVS_AGENT_CHART
    namespace = APP_NAMESPACE

    def teardown():
        get_logger().log_teardown_step("Set enabled attribute to true")
        helm_attribute_keywords.helm_chart_attribute_modify_enabled("true", openvswitch_name, chart_name, namespace)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Show initial helm override properties and values")
    initial_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    initial_attributes = initial_override_show.get_helm_override_show().get_attributes()
    get_logger().log_info(f"Initial attributes: {initial_attributes}")

    get_logger().log_test_case_step("Set the enabled parameter to false")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("false", openvswitch_name, chart_name, namespace)

    get_logger().log_test_case_step("Verify it was disabled")
    disabled_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    disabled_attributes = disabled_override_show.get_helm_override_show().get_attributes()
    validate_str_contains(str(disabled_attributes), "enabled: false", "Attributes should contain enabled: false")
    get_logger().log_info(f"Disabled attributes: {disabled_attributes}")

    get_logger().log_test_case_step("Set the enabled parameter to true")
    helm_attribute_keywords.helm_chart_attribute_modify_enabled("true", openvswitch_name, chart_name, namespace)

    get_logger().log_test_case_step("Verify it was enabled")
    enabled_override_show = helm_override_keywords.get_system_helm_override_show(openvswitch_name, chart_name, namespace)
    enabled_attributes = enabled_override_show.get_helm_override_show().get_attributes()
    validate_str_contains(str(enabled_attributes), "enabled: true", "Attributes should contain enabled: true")
    get_logger().log_info(f"Enabled attributes: {enabled_attributes}")


@mark.p2
def test_ovsconfig_system_id_override(request: FixtureRequest):
    """
    Verify ovsConfig.systemId helm override is applied to OVSDB.

    Test Steps:
        - Set ovsConfig.systemId override to a custom value
        - Apply openvswitch application
        - Verify system-id in OVSDB external_ids matches the override

    Teardown:
        - Remove the ovsConfig override and re-apply with defaults

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)
    helm_kw = SystemHelmOverrideKeywords(active_ssh_connection)

    custom_system_id = "test-system-123"

    def teardown():
        get_logger().log_teardown_step("Remove ovsConfig override and re-apply")
        helm_kw.delete_system_helm_override(openvswitch_name, OVS_AGENT_CHART, APP_NAMESPACE)
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=openvswitch_name, timeout=600)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Set ovsConfig.systemId override")
    helm_kw.update_helm_override_via_set(f"ovsConfig.systemId={custom_system_id}", openvswitch_name, OVS_AGENT_CHART, APP_NAMESPACE)

    get_logger().log_test_case_step("Apply openvswitch application")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=openvswitch_name, timeout=600)

    get_logger().log_test_case_step("Verify system-id in OVSDB external_ids")
    agent_pod = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator").get_pods()[0].get_name()
    output = KubectlExecInPodsKeywords(active_ssh_connection).run_pod_exec_cmd(agent_pod, "ovs-vsctl get open_vswitch . external_ids", options=f"-n {APP_NAMESPACE} -c ovs-vswitchd")
    output_str = "".join(output) if isinstance(output, list) else output
    validate_str_contains(output_str, custom_system_id, "system-id should match override value")


@mark.p2
def test_ovsconfig_stats_update_interval_override(request: FixtureRequest):
    """
    Verify ovsConfig.statsUpdateInterval helm override is applied to OVSDB.

    Test Steps:
        - Set ovsConfig.statsUpdateInterval override to 10000
        - Apply openvswitch application
        - Verify stats-update-interval in OVSDB other_config matches the override

    Teardown:
        - Remove the ovsConfig override and re-apply with defaults

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    openvswitch_name = setup(request, active_ssh_connection)
    helm_kw = SystemHelmOverrideKeywords(active_ssh_connection)

    custom_interval = "10000"

    def teardown():
        get_logger().log_teardown_step("Remove ovsConfig override and re-apply")
        helm_kw.delete_system_helm_override(openvswitch_name, OVS_AGENT_CHART, APP_NAMESPACE)
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=openvswitch_name, timeout=600)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Set ovsConfig.statsUpdateInterval override")
    helm_kw.update_helm_override_via_set(f"ovsConfig.statsUpdateInterval={custom_interval}", openvswitch_name, OVS_AGENT_CHART, APP_NAMESPACE)

    get_logger().log_test_case_step("Apply openvswitch application")
    SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=openvswitch_name, timeout=600)

    get_logger().log_test_case_step("Verify stats-update-interval in OVSDB other_config")
    agent_pod = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator").get_pods()[0].get_name()
    output = KubectlExecInPodsKeywords(active_ssh_connection).run_pod_exec_cmd(agent_pod, "ovs-vsctl get open_vswitch . other_config", options=f"-n {APP_NAMESPACE} -c ovs-vswitchd")
    output_str = "".join(output) if isinstance(output, list) else output
    validate_str_contains(output_str, custom_interval, "stats-update-interval should match override value")


@mark.p2
def test_ovs_manager_ha_pod_recovery(request: FixtureRequest):
    """
    Verify OVS Manager recovers after pod deletion (HA).

    Test Steps:
        - Get current manager pod name
        - Delete the manager pod
        - Verify a new manager pod starts and reaches Running state
        - Verify manager lease still exists

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    get_logger().log_test_case_step("Get current manager pod name")
    pods_kw = KubectlGetPodsKeywords(active_ssh_connection)
    manager_pods = pods_kw.get_pods(namespace=APP_NAMESPACE, label="app=ovs-manager-operator").get_pods()
    validate_not_equals(len(manager_pods), 0, "OVS manager pod exists")
    original_pod_name = manager_pods[0].get_name()
    get_logger().log_info(f"Original manager pod: {original_pod_name}")

    get_logger().log_test_case_step("Delete the manager pod")
    KubectlDeletePodsKeywords(active_ssh_connection).delete_pod(original_pod_name, APP_NAMESPACE)

    get_logger().log_test_case_step("Verify new manager pod starts and reaches Running state")
    pods_kw.wait_for_pods_to_reach_status(expected_status="Running", namespace=APP_NAMESPACE, timeout=120)
    new_manager_pods = pods_kw.get_pods(namespace=APP_NAMESPACE, label="app=ovs-manager-operator").get_pods()
    validate_not_equals(len(new_manager_pods), 0, "New manager pod exists")
    new_pod_name = new_manager_pods[0].get_name()
    validate_not_equals(new_pod_name, original_pod_name, "New pod is different from deleted pod")
    get_logger().log_info(f"New manager pod: {new_pod_name}")

    get_logger().log_test_case_step("Verify manager lease still exists")
    lease_output = KubectlGetLeaseKeywords(active_ssh_connection).get_leases(APP_NAMESPACE)
    lease_holders = lease_output.get_lease_holders()
    validate_equals(any("ovs-manager" in h for h in lease_holders), True, "OVS manager lease should exist")


@mark.p2
def test_ovs_bridge_crd_operations(request: FixtureRequest):
    """
    Verify OVSBridge CRD create and delete operations.

    Test Steps:
        - Create OVSBridge CR via YAML
        - Verify bridge exists in OVS
        - Delete OVSBridge CR
        - Verify bridge is removed from OVS

    Teardown:
        - Delete OVSBridge CR and YAML file if still present

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    file_keywords = FileKeywords(active_ssh_connection)
    delete_resource_keywords = KubectlDeleteResourceKeywords(active_ssh_connection)
    exec_keywords = KubectlExecInPodsKeywords(active_ssh_connection)

    def teardown():
        get_logger().log_teardown_step("Delete OVSBridge CR and YAML file")
        delete_resource_keywords.delete_resource("ovsbridge", OVS_BRIDGE_NAME, namespace=APP_NAMESPACE)
        file_keywords.delete_file(OVS_BRIDGE_YAML_PATH)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step("Create bridge YAML file")
    file_keywords.create_directory(OVS_BRIDGE_YAML_DIR)
    file_keywords.create_file_with_heredoc(OVS_BRIDGE_YAML_PATH, OVS_BRIDGE_YAML)

    get_logger().log_test_case_step("Create OVSBridge CR")
    KubectlFileApplyKeywords(active_ssh_connection).apply_resource_from_yaml(OVS_BRIDGE_YAML_PATH)

    get_logger().log_test_case_step("Verify bridge exists in OVS")
    agent_pod = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator").get_pods()[0].get_name()
    output = exec_keywords.run_pod_exec_cmd(agent_pod, "ovs-vsctl list-br", options=f"-n {APP_NAMESPACE} -c ovs-vswitchd")
    output_str = "".join(output) if isinstance(output, list) else output
    validate_str_contains(output_str, OVS_BRIDGE_NAME, "Bridge should exist in OVS")

    get_logger().log_test_case_step("Delete OVSBridge CR")
    delete_resource_keywords.delete_resource("ovsbridge", OVS_BRIDGE_NAME, namespace=APP_NAMESPACE)

    get_logger().log_test_case_step("Verify bridge is removed from OVS")
    output = exec_keywords.run_pod_exec_cmd(agent_pod, "ovs-vsctl list-br", options=f"-n {APP_NAMESPACE} -c ovs-vswitchd")
    output_str = "".join(output) if isinstance(output, list) else output
    validate_not_equals(OVS_BRIDGE_NAME in output_str, True, "Bridge should be removed from OVS")


@mark.p2
@mark.lab_has_standby_controller
def test_lock_unlock_active_controller_openvswitch(request: FixtureRequest):
    """Verify openvswitch app survives lock/unlock of the (originally active) controller.

    Test Steps:
        - Get active controller name
        - Swact activity to the standby, reconnect to new active
        - Verify app still applied after swact
        - Lock the originally-active controller (now standby)
        - Unlock it and wait for it to be available
        - Verify agent pod running on the unlocked node

    Teardown:
        - Unlock the originally-active controller if still locked

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    host_list_keywords = SystemHostListKeywords(active_ssh_connection)
    orig_active_name = host_list_keywords.get_active_controller().get_host_name()

    def teardown():
        get_logger().log_teardown_step(f"Ensure {orig_active_name} is unlocked")
        teardown_ssh = LabConnectionKeywords().get_active_controller_ssh()
        teardown_lock = SystemHostLockKeywords(teardown_ssh)
        if teardown_lock.is_host_locked(orig_active_name):
            teardown_lock.unlock_host(orig_active_name)
            teardown_lock.wait_for_host_unlocked(orig_active_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Swact activity away from active controller {orig_active_name}")
    swact_success = SystemHostSwactKeywords(active_ssh_connection).host_swact()
    validate_equals(swact_success, True, "Controller swact should succeed")

    get_logger().log_test_case_step("Reconnect to new active controller")
    new_ssh = LabConnectionKeywords().get_active_controller_ssh()
    new_lock_keywords = SystemHostLockKeywords(new_ssh)

    get_logger().log_test_case_step("Verify app still applied after swact")
    SystemApplicationListKeywords(new_ssh).validate_app_status(APP_NAME, "applied", timeout=60)

    get_logger().log_test_case_step(f"Lock originally-active controller {orig_active_name} (now standby)")
    lock_success = new_lock_keywords.lock_host(orig_active_name)
    validate_equals(lock_success, True, "Originally-active controller should lock successfully")
    new_lock_keywords.wait_for_host_locked(orig_active_name)

    get_logger().log_test_case_step("Verify app still applied while host locked")
    SystemApplicationListKeywords(new_ssh).validate_app_status(APP_NAME, "applied", timeout=60)

    get_logger().log_test_case_step(f"Unlock {orig_active_name}")
    unlock_success = new_lock_keywords.unlock_host(orig_active_name)
    validate_equals(unlock_success, True, "Controller should unlock successfully")
    new_lock_keywords.wait_for_host_unlocked(orig_active_name)

    get_logger().log_test_case_step(f"Verify agent pod running on {orig_active_name} after unlock")

    def get_agent_status_on_orig_active():
        pods = KubectlGetPodsKeywords(new_ssh).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator")
        node_pods = pods.get_pods_on_node(orig_active_name)
        if not node_pods:
            return "NoPod"
        return node_pods[0].get_status()

    validate_equals_with_retry(get_agent_status_on_orig_active, "Running", f"Agent pod on {orig_active_name} should be Running after unlock", timeout=120, polling_sleep_time=5)

    get_logger().log_test_case_step(f"Swact activity back to restore {orig_active_name} as active")
    SystemHostSwactKeywords(new_ssh).host_swact()
    restored_ssh = LabConnectionKeywords().get_active_controller_ssh()
    restored_active_name = SystemHostListKeywords(restored_ssh).get_active_controller().get_host_name()
    validate_equals(restored_active_name, orig_active_name, f"{orig_active_name} should be active again after swact back")


@mark.p2
@mark.lab_has_standby_controller
def test_lock_unlock_standby_controller_openvswitch(request: FixtureRequest):
    """Verify openvswitch app survives lock/unlock of standby controller.

    Test Steps:
        - Lock standby controller
        - Verify app still applied and agent running on active
        - Unlock standby controller
        - Wait for host to be available
        - Verify agent pod comes back on the unlocked node

    Teardown:
        - Unlock standby if still locked

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    host_list_keywords = SystemHostListKeywords(active_ssh_connection)
    lock_keywords = SystemHostLockKeywords(active_ssh_connection)

    standby = host_list_keywords.get_standby_controller()
    standby_name = standby.get_host_name()

    def teardown():
        get_logger().log_teardown_step(f"Ensure {standby_name} is unlocked")
        if lock_keywords.is_host_locked(standby_name):
            lock_keywords.unlock_host(standby_name)
            lock_keywords.wait_for_host_unlocked(standby_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Lock standby controller {standby_name}")
    lock_success = lock_keywords.lock_host(standby_name)
    validate_equals(lock_success, True, "Standby controller should lock successfully")
    lock_keywords.wait_for_host_locked(standby_name)

    get_logger().log_test_case_step("Verify app still applied on active")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Verify agent pod still running on active")
    active_name = host_list_keywords.get_active_controller().get_host_name()
    pods_output = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator")
    agent_pods_on_active = pods_output.get_pods_on_node(active_name)
    validate_not_equals(len(agent_pods_on_active), 0, f"Agent pod should exist on active node {active_name}")
    validate_equals(agent_pods_on_active[0].get_status(), "Running", f"Agent pod on {active_name} should be Running")

    get_logger().log_test_case_step(f"Unlock standby controller {standby_name}")
    unlock_success = lock_keywords.unlock_host(standby_name)
    validate_equals(unlock_success, True, "Standby controller should unlock successfully")
    lock_keywords.wait_for_host_unlocked(standby_name)

    get_logger().log_test_case_step(f"Verify agent pod running on {standby_name} after unlock")

    def get_agent_status_on_standby():
        pods = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator")
        node_pods = pods.get_pods_on_node(standby_name)
        if not node_pods:
            return "NoPod"
        return node_pods[0].get_status()

    validate_equals_with_retry(get_agent_status_on_standby, "Running", f"Agent pod on {standby_name} should be Running after unlock", timeout=120, polling_sleep_time=5)


@mark.p2
@mark.lab_has_standby_controller
def test_swact_openvswitch(request: FixtureRequest):
    """Verify openvswitch app survives controller swact.

    Test Steps:
        - Verify app is applied before swact
        - Perform controller swact
        - Reconnect to new active controller
        - Verify app still applied
        - Verify manager and agent pods running on new active
        - Swact back to restore the original active controller

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    get_logger().log_test_case_step("Verify app applied before swact")
    SystemApplicationListKeywords(active_ssh_connection).validate_app_status(APP_NAME, "applied", timeout=30)

    get_logger().log_test_case_step("Perform controller swact")
    swact_success = SystemHostSwactKeywords(active_ssh_connection).host_swact()
    validate_equals(swact_success, True, "Controller swact should succeed")

    get_logger().log_test_case_step("Reconnect to new active controller")
    new_ssh = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify app still applied after swact")
    SystemApplicationListKeywords(new_ssh).validate_app_status(APP_NAME, "applied", timeout=60)

    get_logger().log_test_case_step("Verify manager pod running on new active")
    new_active_name = SystemHostListKeywords(new_ssh).get_active_controller().get_host_name()

    def get_manager_status_on_new_active():
        pods = KubectlGetPodsKeywords(new_ssh).get_pods(namespace=APP_NAMESPACE, label="app=ovs-manager-operator")
        node_pods = pods.get_pods_on_node(new_active_name)
        if not node_pods:
            return "NoPod"
        return node_pods[0].get_status()

    validate_equals_with_retry(get_manager_status_on_new_active, "Running", f"Manager pod on {new_active_name} should be Running after swact", timeout=120, polling_sleep_time=5)

    get_logger().log_test_case_step("Verify agent pod running on new active")

    def get_agent_status_on_new_active():
        pods = KubectlGetPodsKeywords(new_ssh).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator")
        node_pods = pods.get_pods_on_node(new_active_name)
        if not node_pods:
            return "NoPod"
        return node_pods[0].get_status()

    validate_equals_with_retry(get_agent_status_on_new_active, "Running", f"Agent pod on {new_active_name} should be Running after swact", timeout=120, polling_sleep_time=5)

    get_logger().log_test_case_step("Swact back to restore the original active controller")
    swact_back_success = SystemHostSwactKeywords(new_ssh).host_swact()
    validate_equals(swact_back_success, True, "Controller swact back should complete successfully")


@mark.p2
@mark.lab_has_worker
def test_worker_lock_unlock_openvswitch(request: FixtureRequest):
    """Verify openvswitch agent pod restarts after worker node lock/unlock.

    Test Steps:
        - Identify a worker node with an agent pod
        - Lock the worker
        - Unlock the worker
        - Verify agent pod comes back Running on the worker

    Teardown:
        - Unlock worker if still locked

    Args:
        request (FixtureRequest): pytest request fixture for test setup and teardown
    """
    active_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    setup(request, active_ssh_connection)

    host_list_keywords = SystemHostListKeywords(active_ssh_connection)
    lock_keywords = SystemHostLockKeywords(active_ssh_connection)

    hosts = host_list_keywords.get_system_host_list().get_hosts()
    worker_name = None
    for host in hosts:
        if host.get_personality() == "worker" and host.get_administrative() == "unlocked":
            worker_name = host.get_host_name()
            break
    validate_not_equals(worker_name, None, "Should find an unlocked worker node")

    def teardown():
        get_logger().log_teardown_step(f"Ensure {worker_name} is unlocked")
        if lock_keywords.is_host_locked(worker_name):
            lock_keywords.unlock_host(worker_name)
            lock_keywords.wait_for_host_unlocked(worker_name)

    request.addfinalizer(teardown)

    get_logger().log_test_case_step(f"Lock worker {worker_name}")
    lock_success = lock_keywords.lock_host(worker_name)
    validate_equals(lock_success, True, "Worker should lock successfully")
    lock_keywords.wait_for_host_locked(worker_name)

    get_logger().log_test_case_step(f"Unlock worker {worker_name}")
    unlock_success = lock_keywords.unlock_host(worker_name)
    validate_equals(unlock_success, True, "Worker should unlock successfully")
    lock_keywords.wait_for_host_unlocked(worker_name)

    get_logger().log_test_case_step(f"Verify agent pod running on {worker_name} after unlock")

    def get_agent_status_on_worker():
        pods = KubectlGetPodsKeywords(active_ssh_connection).get_pods(namespace=APP_NAMESPACE, label="app=ovs-agent-operator")
        node_pods = pods.get_pods_on_node(worker_name)
        if not node_pods:
            return "NoPod"
        return node_pods[0].get_status()

    validate_equals_with_retry(get_agent_status_on_worker, "Running", f"Agent pod on {worker_name} should be Running after unlock", timeout=120, polling_sleep_time=5)

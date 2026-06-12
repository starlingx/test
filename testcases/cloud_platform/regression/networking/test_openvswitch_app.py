"""Test suite for the openvswitch platform application lifecycle.

This test suite covers upload, apply, remove, delete, helm overrides,
and chart attribute modifications for the openvswitch application.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_not_equals, validate_str_contains
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

APP_NAME = "openvswitch"
APP_NAMESPACE = "openvswitch"
OVS_AGENT_CHART = "ovs-agent"
OVS_MANAGER_CHART = "ovs-manager"
BASE_APPLICATION_PATH = "/usr/local/share/applications/helm/"

# TODO: Remove once tarball static overrides are updated with correct image names
IMAGE_TAG = "stx.13.0-v1.0.0-bullseye"
OVS_AGENT_OVERRIDES = [
    "ovsAgent.image.repository=docker.io/starlingx/stx-ovs-agent-operator",
    f"ovsAgent.image.tag={IMAGE_TAG}",
    "ovsContainer.image.repository=docker.io/starlingx/stx-ovs-container",
    f"ovsContainer.image.tag={IMAGE_TAG}",
]
OVS_MANAGER_OVERRIDES = [
    "ovsManager.image.repository=docker.io/starlingx/stx-ovs-manager-operator",
    f"ovsManager.image.tag={IMAGE_TAG}",
]


def _apply_image_overrides(ssh_connection: SSHConnection) -> None:
    """Apply helm image overrides until tarball static overrides are fixed."""
    helm_kw = SystemHelmOverrideKeywords(ssh_connection)
    helm_kw.helm_override_update_with_list_of_values(APP_NAME, OVS_AGENT_CHART, APP_NAMESPACE, reuse_values=False, set_override=OVS_AGENT_OVERRIDES)
    helm_kw.helm_override_update_with_list_of_values(APP_NAME, OVS_MANAGER_CHART, APP_NAMESPACE, reuse_values=False, set_override=OVS_MANAGER_OVERRIDES)


def setup(request: FixtureRequest, active_ssh_connection: SSHConnection) -> str:
    """
    Setup function to ensure openvswitch is applied before tests.

    Args:
        request (FixtureRequest): pytest request fixture for teardown registration.
        active_ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The openvswitch application name.
    """
    app_list_keywords = SystemApplicationListKeywords(active_ssh_connection)

    if not app_list_keywords.is_app_present(APP_NAME):
        get_logger().log_setup_step("Upload openvswitch app.")
        system_application_upload_input = SystemApplicationUploadInput()
        system_application_upload_input.set_app_name(APP_NAME)
        system_application_upload_input.set_tar_file_path(f"{BASE_APPLICATION_PATH}{APP_NAME}*.tgz")
        SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)

    # TODO: Remove once tarball static overrides are fixed
    get_logger().log_setup_step("Apply image overrides (workaround for incorrect tarball images).")
    _apply_image_overrides(active_ssh_connection)

    app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(APP_NAME)
    current_status = app_show.get_system_application_object().get_status()

    if current_status == "applied":
        get_logger().log_setup_step("App already applied. Skipping apply.")
    else:
        get_logger().log_setup_step("Apply openvswitch app.")
        SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=APP_NAME, timeout=600)

    def cleanup():
        get_logger().log_teardown_step("Cleanup openvswitch app.")
        if app_list_keywords.is_app_present(APP_NAME):
            app_show = SystemApplicationShowKeywords(active_ssh_connection).get_system_application_show(APP_NAME)
            app_status = app_show.get_system_application_object().get_status()

            if app_status == "applied":
                get_logger().log_teardown_step("App is applied - no cleanup needed.")
            elif app_status == "uploaded":
                get_logger().log_teardown_step("Re-apply openvswitch app.")
                SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=APP_NAME)
        else:
            get_logger().log_teardown_step("Re-upload and apply openvswitch app.")
            system_application_upload_input = SystemApplicationUploadInput()
            system_application_upload_input.set_app_name(APP_NAME)
            system_application_upload_input.set_tar_file_path(f"{BASE_APPLICATION_PATH}{APP_NAME}*.tgz")
            SystemApplicationUploadKeywords(active_ssh_connection).system_application_upload(system_application_upload_input)
            SystemApplicationApplyKeywords(active_ssh_connection).system_application_apply(app_name=APP_NAME)

    request.addfinalizer(cleanup)
    return APP_NAME


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
        # TODO: Remove once tarball static overrides are fixed
        get_logger().log_teardown_step("Apply image overrides and apply openvswitch")
        _apply_image_overrides(active_ssh_connection)
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

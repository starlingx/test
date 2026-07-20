from pytest import FixtureRequest

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals, validate_not_none
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.application.object.system_application_status_enum import SystemApplicationStatusEnum
from keywords.cloud_platform.system.application.system_application_apply_keywords import SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_show_keywords import SystemApplicationShowKeywords
from keywords.cloud_platform.system.helm.system_helm_override_keywords import SystemHelmOverrideKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.date.date_keywords import DateKeywords
from testcases.cloud_platform.regression.k8s_operator_framework.helper_k8s_operator_framework import (
    cleanup_app,
    download_docker_images_to_local_registry,
    refresh_ostree_and_sysinv,
    setup_input_object_and_upload,
    transfer_app_file_to_active_controller,
)


def test_evaluate_reapply_trigger(request: FixtureRequest):
    """Test the on-demand reapply trigger via helm-override-update --reapply flag.

    Upload and apply an application that declares the on-demand-reapply trigger in its
    metadata.yaml. After applying, perform a helm-override-update with the --reapply flag
    and verify the reapply evaluation is triggered via sysinv.log.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Upload and apply the application
        - Perform helm-override-update with --reapply flag
        - Check sysinv.log for reapply evaluation logs

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    app_version = "1.0-1"
    app_name = "on-demand-reapply-app"
    chart_name = "adminer"
    namespace = "on-demand"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the app file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    # Capture updated_at before helm-override
    system_app_show = SystemApplicationShowKeywords(ssh_connection)
    app_object_before = system_app_show.get_system_application_show(app_name).get_system_application_object()
    updated_at_before = app_object_before.get_updated_at()

    # Perform helm-override-update with --reapply
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Perform helm-override-update with --reapply for app {app_name}")
    file_keywords = FileKeywords(ssh_connection)
    override_content = "test=1"
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, app_name, chart_name, namespace, reuse_values=True, reapply="--reapply")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Wait for the app to be reapplied by polling updated_at
    get_logger().log_test_case_step(f"Wait for app {app_name} to be reapplied (updated_at changes)")

    system_app_show.validate_app_updated_at_changed(app_name, updated_at_before)

    # Validate app returns to applied status after reapply
    system_app_show.validate_app_status(app_name, SystemApplicationStatusEnum.APPLIED.value)

    # Check sysinv.log for reapply evaluation
    get_logger().log_test_case_step("Check sysinv.log for reapply evaluation logs")
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Evaluate app reapply of {app_name}'")
    validate_not_none(output, "Reapply evaluation log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Auto reapplying {app_name} app'")
    validate_not_none(output, "Auto reapplying log appeared at sysinv.log")


def test_evaluate_reapply_all_trigger(request: FixtureRequest):
    """Test the on-demand reapply trigger via helm-override-update --reapply-all flag.

    Upload and apply an application that declares the on-demand-reapply trigger in its
    metadata.yaml. After applying, perform a helm-override-update with the --reapply-all flag
    and verify the reapply evaluation is triggered via sysinv.log.

    Test Steps:
        - Download docker image required by the app
        - Copy application file to active controller
        - Upload and apply the application
        - Perform helm-override-update with --reapply-all flag
        - Check sysinv.log for reapply evaluation logs

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    app_version = "1.0-2"
    app_name = "on-demand-reapply-app-2"
    chart_name = "adminer-2"
    namespace = "on-demand-2"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_name])

    # Transfer the app file to the active controller
    get_logger().log_test_case_step(f"Copy app {app_name} to active controller")
    transfer_app_file_to_active_controller(app_name, app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload application
    get_logger().log_test_case_step(f"Upload app {app_name}")
    setup_input_object_and_upload(app_name, app_version, ssh_connection)

    # Apply application
    get_logger().log_test_case_step(f"Apply app {app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, "System application object should not be None")
    validate_equals(system_application_object.get_name(), app_name, "Application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, "Application status validation")

    # Capture updated_at before helm-override
    system_app_show = SystemApplicationShowKeywords(ssh_connection)
    app_object_before = system_app_show.get_system_application_show(app_name).get_system_application_object()
    updated_at_before = app_object_before.get_updated_at()

    # Perform helm-override-update with --reapply-all
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Perform helm-override-update with --reapply-all for app {app_name}")
    file_keywords = FileKeywords(ssh_connection)
    override_content = "test=1"
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, app_name, chart_name, namespace, reuse_values=True, reapply="--reapply-all")

    def remove_apps():
        cleanup_app(app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Wait for the app to be reapplied by polling updated_at
    get_logger().log_test_case_step(f"Wait for app {app_name} to be reapplied (updated_at changes)")

    system_app_show.validate_app_updated_at_changed(app_name, updated_at_before)

    # Validate app returns to applied status after reapply
    system_app_show.validate_app_status(app_name, SystemApplicationStatusEnum.APPLIED.value)

    # Check sysinv.log for reapply evaluation
    get_logger().log_test_case_step("Check sysinv.log for reapply evaluation logs")
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Evaluate app reapply of {app_name}'")
    validate_not_none(output, "Reapply evaluation log appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Auto reapplying {app_name} app'")
    validate_not_none(output, "Auto reapplying log appeared at sysinv.log")


def test_evaluate_reapply_all_triggers_reapply_for_all_apps(request: FixtureRequest):
    """Test that --reapply-all triggers reapply evaluation for all applied apps with pending overrides.

    Upload and apply two applications that declare the on-demand-reapply trigger. Perform a
    helm-override-update on the first app WITHOUT any reapply flag (creates pending overrides),
    then perform a helm-override-update on the second app WITH --reapply-all flag. Verify that
    sysinv.log shows reapply evaluation logs for both applications.

    Test Steps:
        - Download docker images required by both apps
        - Copy both application files to active controller
        - Upload and apply both applications
        - Perform helm-override-update on first app without reapply flag
        - Perform helm-override-update on second app with --reapply-all flag
        - Wait for both apps to be reapplied (updated_at changes)
        - Check sysinv.log for reapply evaluation logs for both apps

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    app_1_version = "1.0-1"
    app_1_name = "on-demand-reapply-app"
    app_1_chart_name = "adminer"
    app_1_namespace = "on-demand"

    app_2_version = "1.0-2"
    app_2_name = "on-demand-reapply-app-2"
    app_2_chart_name = "adminer-2"
    app_2_namespace = "on-demand-2"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images for both apps
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_1_name, app_2_name])

    # Transfer both app files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_1_name} and {app_2_name} to active controller")
    transfer_app_file_to_active_controller(app_1_name, app_1_version, ssh_connection)
    transfer_app_file_to_active_controller(app_2_name, app_2_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload both applications
    get_logger().log_test_case_step(f"Upload app {app_1_name}")
    setup_input_object_and_upload(app_1_name, app_1_version, ssh_connection)
    get_logger().log_test_case_step(f"Upload app {app_2_name}")
    setup_input_object_and_upload(app_2_name, app_2_version, ssh_connection)

    # Apply first application
    get_logger().log_test_case_step(f"Apply app {app_1_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_1_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"{app_1_name} application object should not be None")
    validate_equals(system_application_object.get_name(), app_1_name, f"{app_1_name} application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_1_name} application status validation")

    # Apply second application
    get_logger().log_test_case_step(f"Apply app {app_2_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_2_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"{app_2_name} application object should not be None")
    validate_equals(system_application_object.get_name(), app_2_name, f"{app_2_name} application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_2_name} application status validation")

    # Capture updated_at for both apps before helm-overrides
    system_app_show = SystemApplicationShowKeywords(ssh_connection)
    app_1_updated_at_before = system_app_show.get_system_application_show(app_1_name).get_system_application_object().get_updated_at()
    app_2_updated_at_before = system_app_show.get_system_application_show(app_2_name).get_system_application_object().get_updated_at()

    # Perform helm-override-update on first app WITHOUT reapply flag
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Perform helm-override-update without reapply for app {app_1_name}")
    file_keywords = FileKeywords(ssh_connection)
    override_content = "test=1"
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, app_1_name, app_1_chart_name, app_1_namespace, reuse_values=True)

    # Perform helm-override-update on second app WITH --reapply-all flag
    get_logger().log_test_case_step(f"Perform helm-override-update with --reapply-all for app {app_2_name}")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, app_2_name, app_2_chart_name, app_2_namespace, reuse_values=True, reapply="--reapply-all")

    def remove_apps():
        cleanup_app(app_1_name, ssh_connection)
        cleanup_app(app_2_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Wait for both apps to be reapplied by polling updated_at
    get_logger().log_test_case_step(f"Wait for app {app_1_name} to be reapplied (updated_at changes)")
    system_app_show.validate_app_updated_at_changed(app_1_name, app_1_updated_at_before)

    get_logger().log_test_case_step(f"Wait for app {app_2_name} to be reapplied (updated_at changes)")
    system_app_show.validate_app_updated_at_changed(app_2_name, app_2_updated_at_before)

    # Validate both apps return to applied status after reapply
    system_app_show.validate_app_status(app_1_name, SystemApplicationStatusEnum.APPLIED.value)
    system_app_show.validate_app_status(app_2_name, SystemApplicationStatusEnum.APPLIED.value)

    # Check sysinv.log for reapply evaluation logs for both apps
    get_logger().log_test_case_step("Check sysinv.log for reapply evaluation logs for both apps")
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()

    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Evaluate app reapply of {app_1_name}'")
    validate_not_none(output, f"Reapply evaluation log for {app_1_name} appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Auto reapplying {app_1_name} app'")
    validate_not_none(output, f"Auto reapplying log for {app_1_name} appeared at sysinv.log")

    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Evaluate app reapply of {app_2_name}'")
    validate_not_none(output, f"Reapply evaluation log for {app_2_name} appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Auto reapplying {app_2_name} app'")
    validate_not_none(output, f"Auto reapplying log for {app_2_name} appeared at sysinv.log")


def test_reapply_all_does_not_reapply_already_reapplied_app(request: FixtureRequest):
    """Test that --reapply-all does not re-trigger reapply for an app that was already reapplied.

    Upload and apply two applications. Perform a helm-override-update on the first app with
    --reapply and wait for it to complete. Then perform a helm-override-update on the second
    app with --reapply-all. Verify that sysinv.log shows reapply evaluation for the second app
    but NOT for the first app (since it has no new pending overrides after the first reapply).

    Test Steps:
        - Download docker images required by both apps
        - Copy both application files to active controller
        - Upload and apply both applications
        - Perform helm-override-update on first app with --reapply and wait for reapply to complete
        - Perform helm-override-update on second app with --reapply-all
        - Wait for second app to be reapplied
        - Check sysinv.log for reapply evaluation logs for second app only
        - Verify no reapply logs for first app after the second helm-override

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    app_1_version = "1.0-1"
    app_1_name = "on-demand-reapply-app"
    app_1_chart_name = "adminer"
    app_1_namespace = "on-demand"

    app_2_version = "1.0-2"
    app_2_name = "on-demand-reapply-app-2"
    app_2_chart_name = "adminer-2"
    app_2_namespace = "on-demand-2"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images for both apps
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[app_1_name, app_2_name])

    # Transfer both app files to the active controller
    get_logger().log_test_case_step(f"Copy apps {app_1_name} and {app_2_name} to active controller")
    transfer_app_file_to_active_controller(app_1_name, app_1_version, ssh_connection)
    transfer_app_file_to_active_controller(app_2_name, app_2_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload both applications
    get_logger().log_test_case_step(f"Upload app {app_1_name}")
    setup_input_object_and_upload(app_1_name, app_1_version, ssh_connection)
    get_logger().log_test_case_step(f"Upload app {app_2_name}")
    setup_input_object_and_upload(app_2_name, app_2_version, ssh_connection)

    # Apply first application
    get_logger().log_test_case_step(f"Apply app {app_1_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_1_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"{app_1_name} application object should not be None")
    validate_equals(system_application_object.get_name(), app_1_name, f"{app_1_name} application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_1_name} application status validation")

    # Apply second application
    get_logger().log_test_case_step(f"Apply app {app_2_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(app_2_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"{app_2_name} application object should not be None")
    validate_equals(system_application_object.get_name(), app_2_name, f"{app_2_name} application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{app_2_name} application status validation")

    system_app_show = SystemApplicationShowKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    override_content = "test=1"

    # --- Step 1: Helm override on app 1 with --reapply and wait for completion ---
    get_logger().log_test_case_step(f"Perform helm-override-update with --reapply for app {app_1_name}")
    app_1_updated_at_before = system_app_show.get_system_application_show(app_1_name).get_system_application_object().get_updated_at()

    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, app_1_name, app_1_chart_name, app_1_namespace, reuse_values=True, reapply="--reapply")

    get_logger().log_test_case_step(f"Wait for app {app_1_name} to be reapplied (updated_at changes)")
    system_app_show.validate_app_updated_at_changed(app_1_name, app_1_updated_at_before)
    system_app_show.validate_app_status(app_1_name, SystemApplicationStatusEnum.APPLIED.value)

    # Capture app 1 updated_at after its reapply completed (baseline for verifying no second reapply)
    app_1_updated_at_after_reapply = system_app_show.get_system_application_show(app_1_name).get_system_application_object().get_updated_at()

    # --- Step 2: Helm override on app 2 with --reapply-all ---
    get_logger().log_test_case_step(f"Perform helm-override-update with --reapply-all for app {app_2_name}")
    app_2_updated_at_before = system_app_show.get_system_application_show(app_2_name).get_system_application_object().get_updated_at()
    start_date_time_reapply_all = DateKeywords(ssh_connection).get_current_datetime()

    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, app_2_name, app_2_chart_name, app_2_namespace, reuse_values=True, reapply="--reapply-all")

    def remove_apps():
        cleanup_app(app_1_name, ssh_connection)
        cleanup_app(app_2_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Wait for app 2 to be reapplied
    get_logger().log_test_case_step(f"Wait for app {app_2_name} to be reapplied (updated_at changes)")
    system_app_show.validate_app_updated_at_changed(app_2_name, app_2_updated_at_before)
    system_app_show.validate_app_status(app_2_name, SystemApplicationStatusEnum.APPLIED.value)

    # --- Step 3: Check sysinv.log ---
    get_logger().log_test_case_step("Check sysinv.log for reapply evaluation logs")
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()

    # App 2 should have reapply logs
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time_reapply_all, end_date_time, f"'Evaluate app reapply of {app_2_name}'")
    validate_not_none(output, f"Reapply evaluation log for {app_2_name} appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time_reapply_all, end_date_time, f"'Auto reapplying {app_2_name} app'")
    validate_not_none(output, f"Auto reapplying log for {app_2_name} appeared at sysinv.log")

    # App 1 should NOT have been reapplied again (no pending overrides after the first reapply)
    app_1_updated_at_after = system_app_show.get_system_application_show(app_1_name).get_system_application_object().get_updated_at()
    validate_equals(app_1_updated_at_after, app_1_updated_at_after_reapply, f"Application '{app_1_name}' updated_at did not change after --reapply-all (no pending overrides)")


def test_reapply_all_does_not_reapply_app_without_trigger(request: FixtureRequest):
    """Test that --reapply-all does not reapply an app that lacks the on-demand-reapply trigger.

    Upload and apply two applications: one WITHOUT the on-demand-reapply trigger
    (without-trigger-on-demand) and one WITH the trigger (on-demand-reapply-app). Perform a
    helm-override-update on the app without trigger (no reapply flags), then perform a
    helm-override-update on the app with trigger using --reapply-all. Verify that only the app
    with the trigger is reapplied.

    Test Steps:
        - Download docker images required by both apps
        - Copy both application files to active controller
        - Upload and apply both applications
        - Perform helm-override-update on without-trigger app without reapply flags
        - Perform helm-override-update on on-demand-reapply-app with --reapply-all
        - Wait for on-demand-reapply-app to be reapplied
        - Verify without-trigger app was NOT reapplied (updated_at unchanged)
        - Check sysinv.log for reapply evaluation logs for on-demand-reapply-app only

    Args:
        request (FixtureRequest): pytest fixture for managing test setup and teardown.
    """
    no_trigger_app_version = "1.0-1"
    no_trigger_app_name = "without-trigger-on-demand"
    no_trigger_chart_name = "adminer-without"
    no_trigger_namespace = "without-on-demand"

    trigger_app_version = "1.0-1"
    trigger_app_name = "on-demand-reapply-app"
    trigger_chart_name = "adminer"
    trigger_namespace = "on-demand"

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    # Download docker images for both apps
    download_docker_images_to_local_registry(request, ssh_connection, namespaces=[no_trigger_app_name, trigger_app_name])

    # Transfer both app files to the active controller
    get_logger().log_test_case_step(f"Copy apps {no_trigger_app_name} and {trigger_app_name} to active controller")
    transfer_app_file_to_active_controller(no_trigger_app_name, no_trigger_app_version, ssh_connection)
    transfer_app_file_to_active_controller(trigger_app_name, trigger_app_version, ssh_connection)
    refresh_ostree_and_sysinv(ssh_connection)

    # Upload both applications
    get_logger().log_test_case_step(f"Upload app {no_trigger_app_name}")
    setup_input_object_and_upload(no_trigger_app_name, no_trigger_app_version, ssh_connection)
    get_logger().log_test_case_step(f"Upload app {trigger_app_name}")
    setup_input_object_and_upload(trigger_app_name, trigger_app_version, ssh_connection)

    # Apply without-trigger app
    get_logger().log_test_case_step(f"Apply app {no_trigger_app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(no_trigger_app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"{no_trigger_app_name} application object should not be None")
    validate_equals(system_application_object.get_name(), no_trigger_app_name, f"{no_trigger_app_name} application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{no_trigger_app_name} application status validation")

    # Apply on-demand-reapply-app
    get_logger().log_test_case_step(f"Apply app {trigger_app_name}")
    system_application_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(trigger_app_name)
    system_application_object = system_application_apply_output.get_system_application_object()
    validate_not_equals(system_application_object, None, f"{trigger_app_name} application object should not be None")
    validate_equals(system_application_object.get_name(), trigger_app_name, f"{trigger_app_name} application name validation")
    validate_equals(system_application_object.get_status(), SystemApplicationStatusEnum.APPLIED.value, f"{trigger_app_name} application status validation")

    system_app_show = SystemApplicationShowKeywords(ssh_connection)
    file_keywords = FileKeywords(ssh_connection)
    override_content = "test=1"

    # Capture updated_at for both apps before helm-overrides
    no_trigger_updated_at_before = system_app_show.get_system_application_show(no_trigger_app_name).get_system_application_object().get_updated_at()
    trigger_updated_at_before = system_app_show.get_system_application_show(trigger_app_name).get_system_application_object().get_updated_at()

    # Perform helm-override-update on without-trigger app WITHOUT reapply flags
    get_logger().log_test_case_step(f"Perform helm-override-update without reapply for app {no_trigger_app_name}")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, no_trigger_app_name, no_trigger_chart_name, no_trigger_namespace, reuse_values=True)

    # Perform helm-override-update on on-demand-reapply-app WITH --reapply-all
    start_date_time = DateKeywords(ssh_connection).get_current_datetime()
    get_logger().log_test_case_step(f"Perform helm-override-update with --reapply-all for app {trigger_app_name}")
    SystemHelmOverrideKeywords(ssh_connection).update_helm_override_via_set(override_content, trigger_app_name, trigger_chart_name, trigger_namespace, reuse_values=True, reapply="--reapply-all")

    def remove_apps():
        cleanup_app(no_trigger_app_name, ssh_connection)
        cleanup_app(trigger_app_name, ssh_connection)
        refresh_ostree_and_sysinv(ssh_connection)

    request.addfinalizer(remove_apps)

    # Wait for on-demand-reapply-app to be reapplied
    get_logger().log_test_case_step(f"Wait for app {trigger_app_name} to be reapplied (updated_at changes)")
    system_app_show.validate_app_updated_at_changed(trigger_app_name, trigger_updated_at_before)
    system_app_show.validate_app_status(trigger_app_name, SystemApplicationStatusEnum.APPLIED.value)

    # Verify without-trigger app was NOT reapplied (updated_at unchanged)
    get_logger().log_test_case_step(f"Verify app {no_trigger_app_name} was NOT reapplied")
    no_trigger_updated_at_after = system_app_show.get_system_application_show(no_trigger_app_name).get_system_application_object().get_updated_at()
    validate_equals(no_trigger_updated_at_after, no_trigger_updated_at_before, f"Application '{no_trigger_app_name}' updated_at did not change (no on-demand-reapply trigger)")

    # Check sysinv.log for reapply evaluation logs for on-demand-reapply-app
    get_logger().log_test_case_step("Check sysinv.log for reapply evaluation logs")
    end_date_time = DateKeywords(ssh_connection).get_current_datetime()

    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Evaluate app reapply of {trigger_app_name}'")
    validate_not_none(output, f"Reapply evaluation log for {trigger_app_name} appeared at sysinv.log")
    output = file_keywords.read_file_with_pattern_range("/var/log/sysinv.log", start_date_time, end_date_time, f"'Auto reapplying {trigger_app_name} app'")
    validate_not_none(output, f"Auto reapplying log for {trigger_app_name} appeared at sysinv.log")

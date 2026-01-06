from config.configuration_manager import ConfigurationManager
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

from keywords.cloud_platform.system.application.system_application_list_keywords import \
    SystemApplicationListKeywords
from keywords.cloud_platform.system.application.system_application_upload_keywords import \
    SystemApplicationUploadKeywords
from keywords.cloud_platform.system.application.system_application_apply_keywords import \
    SystemApplicationApplyKeywords
from keywords.cloud_platform.system.application.system_application_remove_keywords import \
    SystemApplicationRemoveKeywords
from keywords.cloud_platform.system.application.system_application_delete_keywords import \
    SystemApplicationDeleteKeywords

from keywords.cloud_platform.system.application.system_application_upload_keywords import \
    SystemApplicationUploadInput
from keywords.cloud_platform.system.application.system_application_remove_keywords import \
    SystemApplicationRemoveInput
from keywords.cloud_platform.system.application.system_application_delete_keywords import \
    SystemApplicationDeleteInput
from keywords.cloud_platform.system.application.object.system_application_status_enum import \
    SystemApplicationStatusEnum

from framework.validation.validation import validate_equals, validate_not_equals
from pytest import mark


@mark.p2
def test_install_power_manager():
    """
    Install (Upload and Apply) Application Power Manager with its dependency Node Feature Discovery

    Raises:
        Exception: If application node-feature-discovery or kubernetes-power-manager failed to upload or apply
    """
    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    base_path = app_config.get_base_application_path()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    power_manager_name = app_config.get_power_manager_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Step 1: Install Node Feature Discovery first

    # Verify if NFD is already installed
    system_applications = SystemApplicationListKeywords(
        ssh_connection).get_system_application_list()

    # If NFD is not already installed, install it
    if not system_applications.is_in_application_list(nfd_name):
        # Setup the upload input object for NFD
        nfd_upload_input = SystemApplicationUploadInput()
        nfd_upload_input.set_app_name(nfd_name)
        nfd_upload_input.set_tar_file_path(f"{base_path}{nfd_name}*.tgz")

        # Upload the NFD app file and verify it
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(nfd_upload_input)
        system_applications = SystemApplicationListKeywords(
            ssh_connection).get_system_application_list()
        nfd_app_status = system_applications.get_application(nfd_name).get_status()
        validate_equals(nfd_app_status, "uploaded", f"{nfd_name} upload status validation")

        # Apply the NFD app to the active controller
        nfd_apply_output = SystemApplicationApplyKeywords(ssh_connection).system_application_apply(
            nfd_name)

        # Verify the NFD app was applied
        nfd_app_object = nfd_apply_output.get_system_application_object()
        validate_not_equals(nfd_app_object, None, f"NFD application object should not be None")
        validate_equals(nfd_app_object.get_name(), nfd_name, f"NFD application name validation")
        validate_equals(nfd_app_object.get_status(), SystemApplicationStatusEnum.APPLIED.value,
                        f"NFD application status validation")
    else:
        # Verify NFD is already applied
        nfd_status = system_applications.get_application(nfd_name).get_status()
        validate_equals(nfd_status, SystemApplicationStatusEnum.APPLIED.value,
                        f"NFD application should be in applied state")

    # Step 2: Install Power Manager

    # Verify the Power Manager app is not present in the system
    system_applications = SystemApplicationListKeywords(
        ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(power_manager_name):
        # If already installed, verify it's in applied state
        power_manager_status = system_applications.get_application(power_manager_name).get_status()
        if power_manager_status == SystemApplicationStatusEnum.APPLIED.value:
            return
    else:
        # Setup the upload input object for Power Manager
        power_manager_upload_input = SystemApplicationUploadInput()
        power_manager_upload_input.set_app_name(power_manager_name)
        power_manager_upload_input.set_tar_file_path(f"{base_path}{power_manager_name}*.tgz")

        # Upload the Power Manager app file and verify it
        SystemApplicationUploadKeywords(ssh_connection).system_application_upload(
            power_manager_upload_input)
        system_applications = SystemApplicationListKeywords(
            ssh_connection).get_system_application_list()
        power_manager_app_status = system_applications.get_application(
            power_manager_name).get_status()
        validate_equals(power_manager_app_status, "uploaded",
                        f"{power_manager_name} upload status validation")

        # Apply the Power Manager app to the active controller
    power_manager_apply_output = SystemApplicationApplyKeywords(
        ssh_connection).system_application_apply(power_manager_name)

    # Verify the Power Manager app was applied
    power_manager_app_object = power_manager_apply_output.get_system_application_object()
    validate_not_equals(power_manager_app_object, None,
                        f"Power Manager application object should not be None")
    validate_equals(power_manager_app_object.get_name(), power_manager_name,
                    f"Power Manager application name validation")
    validate_equals(power_manager_app_object.get_status(),
                    SystemApplicationStatusEnum.APPLIED.value,
                    f"Power Manager application status validation")


@mark.p2
def test_uninstall_power_manager():
    """
    Uninstall (Remove and Delete) Application Power Manager and its dependency Node Feature Discovery

    Raises:
        Exception: If application Power Manager or Node Feature Discovery failed to remove or delete
    """
    # Setup app configs and lab connection
    app_config = ConfigurationManager.get_app_config()
    power_manager_name = app_config.get_power_manager_app_name()
    nfd_name = app_config.get_node_feature_discovery_app_name()
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    # Step 1: Uninstall Power Manager first (since it depends on NFD)

    # Verify if the Power Manager app is present in the system
    system_applications = SystemApplicationListKeywords(
        ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(power_manager_name):
        # Remove the Power Manager application
        power_manager_status = system_applications.get_application(power_manager_name).get_status()
        power_manager_remove_input = SystemApplicationRemoveInput()
        power_manager_remove_input.set_app_name(power_manager_name)
        power_manager_remove_input.set_force_removal(False)
        if power_manager_status == SystemApplicationStatusEnum.APPLIED.value:
            power_manager_output = SystemApplicationRemoveKeywords(
                ssh_connection).system_application_remove(power_manager_remove_input)
            validate_equals(power_manager_output.get_system_application_object().get_status(),
                            SystemApplicationStatusEnum.UPLOADED.value,
                            f"Power Manager removal status validation")

        # Delete the Power Manager application
        power_manager_delete_input = SystemApplicationDeleteInput()
        power_manager_delete_input.set_app_name(power_manager_name)
        power_manager_delete_input.set_force_deletion(False)
        power_manager_delete_msg = SystemApplicationDeleteKeywords(
            ssh_connection).get_system_application_delete(power_manager_delete_input)
        validate_equals(power_manager_delete_msg, f"Application {power_manager_name} deleted.\n",
                        f"Power Manager deletion message validation")

    # Step 2: Uninstall Node Feature Discovery

    # Verify if the NFD app is present in the system
    system_applications = SystemApplicationListKeywords(
        ssh_connection).get_system_application_list()
    if system_applications.is_in_application_list(nfd_name):
        # Remove the NFD application
        nfd_app_status = system_applications.get_application(nfd_name).get_status()
        nfd_remove_input = SystemApplicationRemoveInput()
        nfd_remove_input.set_app_name(nfd_name)
        nfd_remove_input.set_force_removal(False)
        if nfd_app_status == SystemApplicationStatusEnum.APPLIED.value:
            nfd_output = SystemApplicationRemoveKeywords(ssh_connection).system_application_remove(
                nfd_remove_input)
            validate_equals(nfd_output.get_system_application_object().get_status(),
                            SystemApplicationStatusEnum.UPLOADED.value,
                            f"NFD removal status validation")

        # Delete the NFD application
        nfd_delete_input = SystemApplicationDeleteInput()
        nfd_delete_input.set_app_name(nfd_name)
        nfd_delete_input.set_force_deletion(False)
        nfd_delete_msg = SystemApplicationDeleteKeywords(
            ssh_connection).get_system_application_delete(nfd_delete_input)
        validate_equals(nfd_delete_msg, f"Application {nfd_name} deleted.\n",
                        f"NFD deletion message validation")
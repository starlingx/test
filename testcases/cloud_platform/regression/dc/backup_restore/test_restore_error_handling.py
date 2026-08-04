"""
DC restore error handling validation.

Validates that dcmanager produces clear, actionable troubleshooting guidance
when users provide invalid flag combinations or parameters during subcloud
backup restore operations.
"""

from pytest import FixtureRequest, mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_not_equals, validate_str_contains
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_backup_keywords import DcManagerSubcloudBackupKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

REGISTRY_WITHOUT_LOCAL_ONLY_ERROR = "Option --registry-images cannot be used without --local-only option."
RELEASE_WITHOUT_INSTALL_OR_FACTORY_ERROR = "Option --release cannot be used without --with-install or --factory option."
BOTH_SUBCLOUD_AND_GROUP_ERROR = "The command only applies to a single subcloud or a subcloud group, not both."
MISSING_SUBCLOUD_OR_GROUP_ERROR = "Please provide the subcloud or subcloud group name or id."
AUTO_RESTORE_RELEASE_TOO_OLD_ERROR = "not supported for releases earlier than"
RESTORE_PASSWORD_PROMPT = "Enter the sysadmin password for the subcloud"


@mark.p2
@mark.lab_has_subcloud
def test_restore_rejects_registry_images_without_local_only(request: FixtureRequest):
    """Verify dcmanager rejects restore when --registry-images is used without --local-only.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.

    Test Steps:
        1. Run dcmanager subcloud-backup restore with --registry-images but without --local-only.
        2. Validate command is rejected with appropriate error.

    Expected Results:
        - Command returns non-zero exit code.
        - Error output contains the expected error about registry-images requiring local-only.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(sysadmin_password=subcloud_password, subcloud=subcloud_name, registry=True, local_only=False)

    if rc == 0:
        get_logger().log_info("UNEXPECTED: restore accepted. Manual cleanup may be needed.")

    validate_not_equals(rc, 0, f"Command should be rejected (non-zero rc). Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), REGISTRY_WITHOUT_LOCAL_ONLY_ERROR.lower(), "Error about registry-images requiring local-only")


@mark.p2
@mark.lab_has_subcloud
def test_restore_rejects_release_without_install_or_factory(request: FixtureRequest):
    """Verify dcmanager rejects restore when --release is used without --with-install or --factory.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.

    Test Steps:
        1. Run dcmanager subcloud-backup restore with --release but without --with-install or --factory.
        2. Validate command is rejected with appropriate error.

    Expected Results:
        - Command returns non-zero exit code.
        - Error output contains the expected error about release requiring with-install or factory.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(sysadmin_password=subcloud_password, subcloud=subcloud_name, release="25.09")

    if rc == 0:
        get_logger().log_info("UNEXPECTED: restore accepted. Manual cleanup may be needed.")

    validate_not_equals(rc, 0, f"Command should be rejected (non-zero rc). Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), RELEASE_WITHOUT_INSTALL_OR_FACTORY_ERROR.lower(), "Error about release requiring with-install or factory")


@mark.p2
@mark.lab_has_subcloud
def test_restore_rejects_both_subcloud_and_group(request: FixtureRequest):
    """Verify dcmanager rejects restore when both --subcloud and --group are provided.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.

    Test Steps:
        1. Run dcmanager subcloud-backup restore with both --subcloud and --group.
        2. Validate command is rejected with appropriate error.

    Expected Results:
        - Command returns non-zero exit code.
        - Error output contains the expected error about not using both parameters.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(sysadmin_password=subcloud_password, subcloud=subcloud_name, group="Default")

    if rc == 0:
        get_logger().log_info("UNEXPECTED: restore accepted. Manual cleanup may be needed.")

    validate_not_equals(rc, 0, f"Command should be rejected (non-zero rc). Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), BOTH_SUBCLOUD_AND_GROUP_ERROR.lower(), "Error about using both subcloud and group")


@mark.p2
@mark.lab_has_subcloud
def test_restore_rejects_missing_subcloud_and_group(request: FixtureRequest):
    """Verify dcmanager rejects restore when neither --subcloud nor --group is provided.

    Preconditions:
        - System controller is accessible.

    Test Steps:
        1. Run dcmanager subcloud-backup restore without --subcloud or --group.
        2. Validate command is rejected with appropriate error.

    Expected Results:
        - Command returns non-zero exit code.
        - Error output contains the expected error about providing subcloud or group.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(sysadmin_password=subcloud_password)

    if rc == 0:
        get_logger().log_info("UNEXPECTED: restore accepted. Manual cleanup may be needed.")

    validate_not_equals(rc, 0, f"Command should be rejected (non-zero rc). Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), MISSING_SUBCLOUD_OR_GROUP_ERROR.lower(), "Error about providing subcloud or group")


@mark.p2
@mark.lab_has_subcloud
def test_restore_rejects_auto_with_old_release(request: FixtureRequest):
    """Verify dcmanager rejects auto restore when release is earlier than 26.03.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.
        - Subcloud must be unmanaged for restore to reach server validation.

    Test Steps:
        1. Run dcmanager subcloud-backup restore with --auto and --release 25.03.
        2. Validate command is rejected with appropriate error.

    Expected Results:
        - Command returns non-zero exit code.
        - Error output contains the expected error about releases earlier than 26.03.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]
    lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
    subcloud_password = lab_config.get_admin_credentials().get_password()

    output, rc = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_with_error(sysadmin_password=subcloud_password, subcloud=subcloud_name, auto_restore=True, with_install=True, release="25.03")

    if rc == 0:
        get_logger().log_info("UNEXPECTED: restore accepted. Manual cleanup may be needed.")

    validate_not_equals(rc, 0, f"Command should be rejected (non-zero rc). Got rc={rc}. Output: {output}")
    validate_str_contains(output.lower(), AUTO_RESTORE_RELEASE_TOO_OLD_ERROR.lower(), "Error about release being too old for auto restore")


@mark.p2
@mark.lab_has_subcloud
def test_restore_prompts_for_password_when_not_provided(request: FixtureRequest):
    """Verify dcmanager prompts for sysadmin password when --sysadmin-password is omitted.

    Tests the troubleshooting behavior where a user forgets to provide the
    password flag and the CLI interactively asks for it rather than failing.

    Preconditions:
        - Lab has at least one subcloud with deployment assets configured.
        - System controller is accessible.

    Test Steps:
        1. Run dcmanager subcloud-backup restore without --sysadmin-password.
        2. Validate the CLI prompts for the password interactively.
        3. Cancel the command with Ctrl+C.

    Expected Results:
        - The CLI outputs a password prompt containing expected text.
        - No subcloud state is changed.
    """
    system_controller_ssh = LabConnectionKeywords().get_active_controller_ssh()
    subcloud_name = ConfigurationManager.get_lab_config().get_subcloud_names()[0]

    get_logger().log_test_case_step("Running restore without --sysadmin-password to trigger prompt")
    prompt_output = DcManagerSubcloudBackupKeywords(system_controller_ssh).restore_subcloud_backup_prompt_check(subcloud=subcloud_name)

    get_logger().log_info(f"Prompt output: {prompt_output}")

    validate_str_contains(
        prompt_output.lower(),
        RESTORE_PASSWORD_PROMPT.lower(),
        "CLI prompts for sysadmin password when not provided",
    )

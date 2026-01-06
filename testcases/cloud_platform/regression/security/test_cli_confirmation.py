from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.host.system_host_lock_keywords import SystemHostLockKeywords
from keywords.cloud_platform.system.service.system_service_keywords import SystemServiceKeywords


def cli_confirmations_enabled(request: FixtureRequest):
    """
    Function to enable CLI confirmations in setup and disable in teardown.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceKeywords(ssh_connection)

    get_logger().log_info("Enabling CLI confirmations in setup")
    service_keywords.modify_service_parameter("platform", "client", "cli_confirmations", "enabled")
    service_keywords.apply_service_parameters("platform")

    get_logger().log_info("Waiting for CLI confirmation settings to take effect...")
    # Exit from lab session to force fresh login
    get_logger().log_info("Exiting from lab session to force fresh login")
    ssh_connection.send("exit")
    ssh_connection.close()

    # Completely destroy the connection object
    ssh_connection = None
    get_logger().log_info("Setup complete - CLI confirmations enabled")

    def teardown():
        teardown_ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
        teardown_service_keywords = SystemServiceKeywords(teardown_ssh_connection)
        get_logger().log_info("Disabling CLI confirmations in teardown")
        teardown_service_keywords.modify_service_parameter("platform", "client", "cli_confirmations", "disabled")
        teardown_service_keywords.apply_service_parameters("platform")

    request.addfinalizer(teardown)


@mark.p1
def test_cli_with_confirmations_enabled(request: FixtureRequest):
    """
    Test system host-lock command with CLI confirmations enabled.
    Verifies confirmation prompts appear for destructive commands.
    """
    # Call the setup function directly
    cli_confirmations_enabled(request)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_info("Testing system host-lock command with confirmations enabled")
    cmd = "system host-lock controller-1"
    command = source_openrc(cmd)

    # Set up prompts to expect confirmation and respond with 'No'
    confirmation_prompt = PromptResponse("Do you want to continue?", "no")
    command_completed = PromptResponse("keystone_admin", None)  # Wait for command prompt to return
    prompts = [confirmation_prompt, command_completed]

    output = ssh_connection.send_expect_prompts(command, prompts)

    # Verify confirmation prompt appeared and was handled correctly
    output_str = str(output)
    get_logger().log_info(f"Full output: {output_str}")

    # Validate that CLI confirmation behavior occurred
    validate_str_contains(output_str, "Operation cancelled by the user", "Verify CLI confirmation prompt appeared and operation was cancelled")

    get_logger().log_info("CLI confirmation prompt appeared and was handled correctly - operation cancelled")

    get_logger().log_info("system host-lock confirmation test completed")


@mark.p1
def test_yes_flag_with_cli_disabled():
    """
    Test system host-lock controller-5 --yes command with CLI confirmations disabled.
    Verifies that --yes flag works properly when CLI confirmations are disabled.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    service_keywords = SystemServiceKeywords(ssh_connection)

    get_logger().log_info("Ensuring CLI confirmations are disabled")
    service_keywords.modify_service_parameter("platform", "client", "cli_confirmations", "disabled")
    service_keywords.apply_service_parameters("platform")

    # Exit from lab session to force fresh login for settings to take effect
    get_logger().log_info("Exiting from lab session to force fresh login")
    ssh_connection.send("exit")
    ssh_connection.close()

    # Create fresh SSH connection to test disabled confirmations
    get_logger().log_info("Creating fresh SSH connection to test disabled confirmations")
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_info("Testing system host-lock controller-5 command without confirmations")

    # Use the keyword to lock host with --yes flag
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    output_str = host_lock_keywords.lock_host_with_error("controller-5", confirm_flag=True)

    get_logger().log_info(f"Command output: {output_str}")

    # Validate that command executed (should get "host not found" message since controller-5 doesn't exist)
    validate_str_contains(output_str, "host not found", "Verify command executed and returned expected error message")

    get_logger().log_info("system host-lock test without confirmation completed")


@mark.p2
def test_yes_flag_with_cli_enabled(request: FixtureRequest):
    """
    Test --yes flag with CLI confirmations enabled using fixture.
    Verifies that --yes flag bypasses confirmation prompts when CLI confirmations are enabled.
    """
    # Call the enabled setup function directly
    cli_confirmations_enabled(request)

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_info("Testing --yes flag with confirmations enabled")

    # Use the keyword to lock host with --yes flag
    host_lock_keywords = SystemHostLockKeywords(ssh_connection)
    output_str = host_lock_keywords.lock_host_with_error("controller-5", confirm_flag=True)

    get_logger().log_info(f"Command output: {output_str}")

    # Validate that command executed (should get "host not found" message since controller-5 doesn't exist)
    validate_str_contains(output_str, "host not found", "Verify command executed and returned expected error message")

    get_logger().log_info("--yes flag test with CLI enabled completed")

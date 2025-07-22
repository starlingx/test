from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.validation.validation import validate_str_contains
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
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

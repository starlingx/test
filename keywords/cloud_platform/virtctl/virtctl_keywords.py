"""Keywords for virtctl client operations."""

from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class VirtctlKeywords(BaseKeyword):
    """Keywords for virtctl client operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize VirtctlKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self._ssh_connection: SSHConnection = ssh_connection

    def virtctl_pause(self, vm_name: str) -> str:
        """Pause a virtual machine.

        Args:
            vm_name (str): Name of the VM to pause.

        Returns:
            str: Command output.
        """
        output = self._ssh_connection.send(f"virtctl pause vm {vm_name}", fail_ok=False)
        self.validate_success_return_code(self._ssh_connection)
        return output

    def login_to_vm(
        self,
        vm_name: str,
        username: str,
        password: str,
        namespace: str = "default",
    ) -> None:
        """Login to a cirros VM via virtctl console and verify it is accessible.

        Opens a new SSH connection, attaches to the VM console, and logs in.

        Example command flow::

            virtctl console vm-cirros
            <login prompt> -> username
            <password prompt> -> password
            $

        Args:
            vm_name (str): Name of the VM to connect to.
            username (str): VM login username.
            password (str): VM login password.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the console login fails.
        """
        get_logger().log_info(f"Opening virtctl console to VM {vm_name}")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse(f"{vm_name}", None),
            PromptResponse("login:", username),
            PromptResponse("assword:", password),
            PromptResponse("$", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"Successfully logged into VM {vm_name}")

    def verify_vm_console_accessible(
        self,
        vm_name: str,
        namespace: str = "default",
    ) -> None:
        """Verify a VM is accessible via virtctl console without full login.

        Connects to the VM console and checks for the 'Successfully connected' message.
        Useful when the VM may already be logged in from a previous session (e.g., after
        live migration) and the login prompt is not expected.

        Args:
            vm_name (str): Name of the VM to connect to.
            namespace (str): Namespace of the VM. Defaults to 'default'.

        Raises:
            KeywordException: If the console connection fails.
        """
        get_logger().log_info(f"Verifying VM {vm_name} console is accessible")

        namespace_flag = f" -n {namespace}" if namespace != "default" else ""
        prompts = [
            PromptResponse("Successfully connected", None),
        ]

        self._ssh_connection.send_expect_prompts(f"virtctl console {vm_name}{namespace_flag}", prompts)
        self.validate_success_return_code(self._ssh_connection)
        get_logger().log_info(f"VM {vm_name} console is accessible")

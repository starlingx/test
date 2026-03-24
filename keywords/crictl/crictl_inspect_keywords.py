from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_is_digit
from keywords.base_keyword import BaseKeyword


class CrictlInspectKeywords(BaseKeyword):
    """Class for 'crictl inspect' keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_container_pid(self, container_id: str) -> int:
        """Get the PID of a container using crictl inspect.

        Args:
            container_id: The containerd container UUID.

        Returns:
            int: The PID of the container process.
        """
        cmd = f"crictl inspect -o go-template --template '{{{{.info.pid}}}}' {container_id}"
        output = self.ssh_connection.send_as_sudo(cmd)
        pid_str = output[0].strip() if isinstance(output, list) else str(output).strip()
        validate_is_digit(pid_str, f"Expected numeric PID, got: {pid_str}")
        return int(pid_str)

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.cat.object.cpu_manager_state_output import CpuManagerStateOutput


class CatCpuManagerStateKeywords(BaseKeyword):
    """Keywords for reading kubelet CPU manager state."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize CatCpuManagerStateKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_cpu_manager_state(self) -> CpuManagerStateOutput:
        """
        Get the content of /var/lib/kubelet/cpu_manager_state.

        Reads the CPU manager state file using sudo cat and parses the JSON.
        Handles sshpass connections where the output may include a Password:
        prefix before the JSON content.

        Returns:
            CpuManagerStateOutput: Parsed CPU manager state object.
        """
        command_output = self.ssh_connection.send_as_sudo("cat /var/lib/kubelet/cpu_manager_state")
        self.validate_success_return_code(self.ssh_connection)

        # Command output is a list of two entries, the first one is the content of the file,
        # with the prompt, and the second one is the prompt again.
        # e.g. [0] = { some JSON }prompt     [1] = prompt
        # When accessed via sshpass, the output may include "Password: " prefix before the JSON.
        cpu_manager_state_output = command_output[0]
        first_brace_index = cpu_manager_state_output.find("{")
        last_brace_index = cpu_manager_state_output.rfind("}")
        cpu_manager_state_output = cpu_manager_state_output[first_brace_index : last_brace_index + 1]

        return CpuManagerStateOutput(cpu_manager_state_output)

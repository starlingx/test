from keywords.base_keyword import BaseKeyword
from keywords.k8s.cat.object.cpu_manager_state_output import CpuManagerStateOutput


class CatCpuManagerStateKeywords(BaseKeyword):
    """
    Class for 'kubectl get ns' keywords
    """

    def __init__(self, ssh_connection):
        """
        Constructor
        Args:
            ssh_connection:
        """
        self.ssh_connection = ssh_connection

    def get_cpu_manager_state(self):
        """
        Gets the content of the file '/var/lib/kubelet/cpu_manager_state' using 'cat' as sudo.
        Args:

        Returns:

        """

        command_output = self.ssh_connection.send_as_sudo("cat /var/lib/kubelet/cpu_manager_state")
        self.validate_success_return_code(self.ssh_connection)

        # Command output is a list of two entries, the first one is the content of the file, with the prompt, and the second one is the prompt again.
        # e.g. [0] = { some JSON }prompt     [1] = prompt
        cpu_manager_state_output = command_output[0]
        last_brace_index = cpu_manager_state_output.rfind('}')
        cpu_manager_state_output = cpu_manager_state_output[0 : last_brace_index + 1]
        namespaces_list_output = CpuManagerStateOutput(cpu_manager_state_output)

        return namespaces_list_output

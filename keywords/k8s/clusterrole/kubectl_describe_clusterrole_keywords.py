from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.k8s.clusterrole.object.kubectl_clusterrole_description_output import KubectlClusterroleDescriptionOutput
from keywords.k8s.k8s_command_wrapper import export_k8s_config


class KubectlDescribeClusterroleKeywords(BaseKeyword):
    """Class for 'kubectl describe clusterrole' keywords."""

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def describe_clusterrole(self, clusterrole_name: str, namespace: str = None) -> KubectlClusterroleDescriptionOutput:
        """Run 'kubectl describe clusterrole <name>' and return parsed output.

        Args:
            clusterrole_name (str): The name of the clusterrole to describe.
            namespace (str): Optional namespace flag.

        Returns:
            KubectlClusterroleDescriptionOutput: Parsed description output.
        """
        cmd = f"kubectl describe clusterrole {clusterrole_name}"
        if namespace:
            cmd += f" -n {namespace}"

        output = self.ssh_connection.send(export_k8s_config(cmd))
        self.validate_success_return_code(self.ssh_connection)
        raw_output = "\n".join(output) if isinstance(output, list) else str(output)
        return KubectlClusterroleDescriptionOutput(raw_output)

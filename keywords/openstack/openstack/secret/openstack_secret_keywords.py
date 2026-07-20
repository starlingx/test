from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.openstack.openstack.secret.object.openstack_secret_output import OpenstackSecretOutput


class OpenstackSecretKeywords(BaseKeyword):
    """Class for OpenStack secret (Barbican) operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the OpenStack controller.
        """
        self.ssh_connection = ssh_connection

    def store_secret(self, name: str, payload: str, payload_content_type: str = "text/plain") -> OpenstackSecretOutput:
        """
        Store a secret in Barbican.

        Args:
            name (str): Name of the secret.
            payload (str): The secret payload data.
            payload_content_type (str): Content type of the payload.

        Returns:
            OpenstackSecretOutput: Parsed output containing the secret href.
        """
        cmd = f"openstack secret store --name {name} --payload {payload} --payload-content-type {payload_content_type}"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        complete_output = "\n".join(output) if isinstance(output, list) else output
        return OpenstackSecretOutput(complete_output)

    def delete_secret(self, secret_href: str) -> str:
        """
        Delete a secret from Barbican.

        Args:
            secret_href (str): The secret href URL to delete.

        Returns:
            str: Command output from secret deletion.
        """
        cmd = f"openstack secret delete {secret_href}"
        output = self.ssh_connection.send(source_openrc(cmd), get_pty=True)
        self.validate_success_return_code(self.ssh_connection)

        return "\n".join(output) if isinstance(output, list) else output

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DockerBuildKeywords(BaseKeyword):
    """Keywords for docker build operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DockerBuildKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def build(self, dockerfile_path: str, tag: str, context_path: str) -> None:
        """Build a docker image from a Dockerfile.

        Args:
            dockerfile_path (str): Path to the Dockerfile on the remote host.
            tag (str): The full image tag (e.g., 'registry.local:9001/kmm/image:tag').
            context_path (str): The build context directory path.
        """
        self.ssh_connection.send_as_sudo(f"docker build -f {dockerfile_path} -t {tag} {context_path}")

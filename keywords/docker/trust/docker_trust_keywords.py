from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DockerTrustKeywords(BaseKeyword):
    """Keywords for Docker trust operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize Docker trust keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def inspect_docker_trust(self, image_name: str, trust_server: str) -> str:
        """Inspect Docker trust signatures for an image.

        Args:
            image_name (str): Name of the Docker image to inspect.
            trust_server (str): Docker trust server URL.

        Returns:
            str: Docker trust inspection output.
        """
        cmd = f"DOCKER_CONTENT_TRUST=1 DOCKER_CONTENT_TRUST_SERVER={trust_server} docker trust inspect {image_name}"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else str(output)

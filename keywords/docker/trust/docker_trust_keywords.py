from framework.logging.automation_logger import get_logger
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

        On Docker 29.x (Trixie), 'docker trust' was removed. In that case,
        skip verification and return a message indicating trust CLI is unavailable.
        Portieris still validates signatures via its admission webhook independently.

        Args:
            image_name (str): Name of the Docker image to inspect.
            trust_server (str): Docker trust server URL.

        Returns:
            str: Docker trust inspection output, or skip message if unavailable.
        """
        cmd = f"DOCKER_CONTENT_TRUST=1 DOCKER_CONTENT_TRUST_SERVER={trust_server} " f"docker trust inspect {image_name}"
        output = self.ssh_connection.send_as_sudo(cmd)
        output_str = "\n".join(output) if isinstance(output, list) else str(output)

        if "unknown command" in output_str:
            get_logger().log_info("docker trust command not available (Docker 29.x). " "Skipping CLI trust verification - portieris validates via webhook.")
            return "Signers: [skipped - docker trust unavailable on Docker 29.x]"

        self.validate_success_return_code(self.ssh_connection)
        return output_str

    def verify_portieris_allowed_image(self, image_name: str, namespace: str = "portieris") -> bool:
        """Verify portieris webhook logs show image was allowed.

        Checks portieris pod logs for 'Allow for images' entry matching the image.
        Use this as alternative verification when docker trust CLI is unavailable.

        Args:
            image_name (str): Image name to check in portieris logs.
            namespace (str): Portieris namespace. Defaults to "portieris".

        Returns:
            bool: True if portieris logs show the image was allowed.
        """
        cmd = f"export KUBECONFIG=/etc/kubernetes/admin.conf; " f"kubectl logs -n {namespace} -l app.kubernetes.io/name=portieris " f"--tail=50 2>&1 | grep -i 'Allow.*{image_name}'"
        output = self.ssh_connection.send(cmd)
        output_str = "\n".join(output) if isinstance(output, list) else str(output)

        if "Allow" in output_str and image_name in output_str:
            get_logger().log_info(f"Portieris webhook confirmed: image {image_name} was ALLOWED")
            return True

        get_logger().log_info(f"Portieris webhook log does not show Allow for {image_name}")
        return False

    def verify_portieris_denied_image(self, image_name: str, namespace: str = "portieris") -> bool:
        """Verify portieris webhook logs show image was denied.

        Args:
            image_name (str): Image name to check in portieris logs.
            namespace (str): Portieris namespace. Defaults to "portieris".

        Returns:
            bool: True if portieris logs show the image was denied.
        """
        cmd = f"export KUBECONFIG=/etc/kubernetes/admin.conf; " f"kubectl logs -n {namespace} -l app.kubernetes.io/name=portieris " f"--tail=50 2>&1 | grep -i 'Deny\\|deny.*{image_name}'"
        output = self.ssh_connection.send(cmd)
        output_str = "\n".join(output) if isinstance(output, list) else str(output)

        if "Deny" in output_str or "deny" in output_str:
            get_logger().log_info(f"Portieris webhook confirmed: image {image_name} was DENIED")
            return True

        get_logger().log_info(f"Portieris webhook log does not show Deny for {image_name}")
        return False

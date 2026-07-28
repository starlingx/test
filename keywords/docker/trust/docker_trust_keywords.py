import re

from framework.exceptions.keyword_exception import KeywordException
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

    def inspect_docker_trust(self, image_name: str, trust_server: str, username: str, password: str) -> str:
        """Inspect Docker trust signatures for an image.

        Tries 'docker trust inspect' first. On Docker 29.x where that subcommand
        was removed, falls back to querying the Notary server REST API directly
        to verify the image has a valid targets role with signed content.

        Args:
            image_name (str): Name of the Docker image to inspect (registry/repo:tag).
            trust_server (str): Docker Notary trust server URL.
            username (str): Registry username for authentication.
            password (str): Registry password for authentication.

        Returns:
            str: Trust inspection output containing signer information.
        """
        cmd = f"DOCKER_CONTENT_TRUST=1 DOCKER_CONTENT_TRUST_SERVER={trust_server} docker trust inspect {image_name}"
        output = self.ssh_connection.send_as_sudo(cmd)
        output_str = "\n".join(output) if isinstance(output, list) else str(output)

        if "unknown command" not in output_str:
            self.validate_success_return_code(self.ssh_connection)
            return output_str

        get_logger().log_info("docker trust not available (Docker 29.x), querying Notary server REST API directly")
        return self.inspect_notary_trust(image_name, trust_server, username, password)

    def inspect_notary_trust(self, image_name: str, trust_server: str, username: str, password: str) -> str:
        """Query the Notary server REST API to verify an image has valid trust data.

        Authenticates against the registry to obtain a Bearer token, then queries
        the Notary server's targets role to confirm signed content exists.

        Args:
            image_name (str): Full image name including registry, repo, and tag
                (e.g. registry:port/repo/image:tag).
            trust_server (str): Notary server base URL (e.g. https://host:port).
            username (str): Registry username for authentication.
            password (str): Registry password for authentication.

        Returns:
            str: JSON response from Notary containing signed targets, including
                signer information.

        Raises:
            KeywordException: If the Notary server returns no trust data or
                the image has no signed targets.
        """
        # Parse GUN: strip registry host:port prefix and tag to get repo path
        # e.g. registry:5000/repo/image:tag -> repo/image
        parts = image_name.split("/", 1)
        repo_and_tag = parts[1] if len(parts) > 1 else image_name
        gun = repo_and_tag.rsplit(":", 1)[0] if ":" in repo_and_tag else repo_and_tag
        registry_host = parts[0]

        # Get Bearer token from registry auth endpoint
        token_url = f"https://{registry_host}/v2/token?service={registry_host}&scope=repository:{gun}:pull"
        token_cmd = f"curl -sk -u {username}:{password} '{token_url}'"
        token_output = self.ssh_connection.send(token_cmd)
        token_str = "\n".join(token_output) if isinstance(token_output, list) else str(token_output)

        token = ""
        if "token" in token_str:
            match = re.search(r'"token"\s*:\s*"([^"]+)"', token_str)
            if match:
                token = match.group(1)

        # Query Notary targets role
        notary_url = f"{trust_server}/v2/{gun}/_trust/tuf/targets.json"
        auth_header = f"-H 'Authorization: Bearer {token}'" if token else f"-u {username}:{password}"
        cmd = f"curl -sk {auth_header} '{notary_url}'"
        output = self.ssh_connection.send(cmd)
        output_str = "\n".join(output) if isinstance(output, list) else str(output)

        if not output_str.strip() or "signed" not in output_str:
            raise KeywordException(f"No trust data found for {image_name} on Notary server {trust_server}")

        get_logger().log_info(f"Notary server confirmed trust data exists for {image_name}")
        return f"Signers: {output_str}"

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

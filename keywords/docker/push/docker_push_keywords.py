from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DockerPushKeywords(BaseKeyword):
    """Keywords for docker push operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DockerPushKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def push(self, image: str) -> None:
        """Push a docker image to a registry.

        Uses send_expect_prompts with a unique end marker to ensure the push
        completes before returning. This is necessary because send_as_sudo can
        return early when sudo credentials are cached due to prompt detection
        matching the initial shell prompt.

        Args:
            image (str): The full image reference to push
                (e.g., 'registry.local:9001/kmm/image:tag').
        """
        get_logger().log_info(f"Pushing docker image: {image}")
        push_end_marker = "DOCKER_PUSH_DONE"
        push_prompts = [
            PromptResponse("assword", self.ssh_connection.password),
            PromptResponse(push_end_marker),
        ]
        self.ssh_connection.send_expect_prompts(
            f"sudo docker push {image}; echo {push_end_marker}",
            push_prompts,
        )

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword

# crictl waits only 2 seconds by default for the image service to answer. Removing a large image
# can take longer, so crictl gives up with "DeadlineExceeded" even though containerd keeps removing
# the image. crictl expects a duration string such as "60s"; a bare number is rejected.
CRICTL_TIMEOUT_SECONDS = 60
# The SSH layer abandons a command that runs longer than its own command timeout, so this must stay
# above the crictl timeout.
CRICTL_SSH_COMMAND_TIMEOUT_SECONDS = CRICTL_TIMEOUT_SECONDS + 30
# Text crictl prints when the image to remove is not in its cache.
NO_SUCH_IMAGE_MESSAGE = "no such image"


class CrictlRmiImagesKeywords(BaseKeyword):
    """
    Class for crictl rmi keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def crictl_rmi_images(self, image_id: str) -> None:
        """
        Remove image

        An image that is not in the crictl cache counts as removed, because the image is absent either
        way. crictl exits with code 1 for that case and for real failures, so the output is checked
        for the "no such image" message to tell them apart.

        Args:
            image_id (str): image id
        """
        output = self.ssh_connection.send_as_sudo(f"crictl --timeout {CRICTL_TIMEOUT_SECONDS}s rmi {image_id}", command_timeout=CRICTL_SSH_COMMAND_TIMEOUT_SECONDS)
        if self.ssh_connection.get_return_code() != 0 and NO_SUCH_IMAGE_MESSAGE in "".join(output):
            get_logger().log_info(f"Image already absent from the crictl cache: {image_id}")
            return
        self.validate_success_return_code(self.ssh_connection)

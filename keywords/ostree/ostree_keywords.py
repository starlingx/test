from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class OstreeKeywords(BaseKeyword):
    """
    Ostree Keywords class
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def ostree_update(self) -> None:
        """
        Simulate an ostree update.
        """
        self.ssh_connection.send_as_sudo("touch /ostree/lock && sudo rm -f /ostree/lock")
        self.validate_success_return_code(self.ssh_connection)

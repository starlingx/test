from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class KeyringKeywords(BaseKeyword):
    """
    Keyring Keywords class
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def get_keyring(self, service: str, identifier: str) -> str:
        """
        Gets a value from the keyring.

        Args:
            service (str): keyring service
            identifier (str): keyring identifier
        Returns:
            The value from the keyring.
        """
        keyring_value = self.ssh_connection.send(f"keyring get {service} {identifier}")
        self.validate_success_return_code(self.ssh_connection)
        return keyring_value[0].strip()
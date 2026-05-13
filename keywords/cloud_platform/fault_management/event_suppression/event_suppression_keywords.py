"""Keywords for FM event suppression commands."""

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class EventSuppressionKeywords(BaseKeyword):
    """Keywords for fm event-suppress and event-unsuppress commands."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self.ssh_connection = ssh_connection

    def suppress_event(self, alarm_id: str) -> None:
        """Suppress an event by alarm ID.

        Args:
            alarm_id (str): The alarm ID to suppress (e.g. '100.106').
        """
        self.ssh_connection.send(source_openrc(f"fm event-suppress --alarm_id {alarm_id} --yes"))
        self.validate_success_return_code(self.ssh_connection)

    def unsuppress_event(self, alarm_id: str) -> None:
        """Unsuppress an event by alarm ID.

        Args:
            alarm_id (str): The alarm ID to unsuppress.
        """
        self.ssh_connection.send(source_openrc(f"fm event-unsuppress --alarm_id {alarm_id}"))
        self.validate_success_return_code(self.ssh_connection)

    def unsuppress_all(self) -> None:
        """Unsuppress all events."""
        self.ssh_connection.send(source_openrc("fm event-unsuppress-all"))
        self.validate_success_return_code(self.ssh_connection)

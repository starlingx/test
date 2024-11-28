from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class SystemDatanetworkDeleteKeywords(BaseKeyword):
    """
    Keywords for deleting the datanetwork
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def delete_datanetwork(self, datanetwork_uuid: str):
        """
        Deletes the datanetwork
        Args:
            datanetwork_uuid (): the uuid of the datanetwork

        Returns:

        """
        self.ssh_connection.send(source_openrc(f'system datanetwork-delete {datanetwork_uuid}'))
        self.validate_success_return_code(self.ssh_connection)

    def cleanup_datanetwork(self, datanetwork_uuid: str):
        """
        Cleanup used for tear downs
        Args:
            datanetwork_uuid (): the datanetwork uuid

        Returns:

        """
        self.ssh_connection.send(source_openrc(f'system datanetwork-delete {datanetwork_uuid}'))
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_error(f"datanetwork with uuid {datanetwork_uuid} failed to delete")
        return rc

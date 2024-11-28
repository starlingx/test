from typing import Optional

from framework.ssh.secure_transfer_file.secure_transfer_file_enum import TransferDirection
from paramiko.sftp_client import SFTPClient


class SecureTransferFileInputObject:
    """
    Class used as input to create an instance of SecureTransferFile. This class carries properties for setting up a new
    SFTP transfer.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.sftp_client: Optional[SFTPClient] = None
        self.destination_path: Optional[str] = None
        self.origin_path: Optional[str] = None
        self.transfer_direction: TransferDirection = TransferDirection.FROM_LOCAL_TO_REMOTE
        self.timeout_in_seconds: int = 60
        self.force: bool = False

    def set_sftp_client(self, sftp_client: SFTPClient):
        """
        Setter for sftp_client.
        """
        self.sftp_client = sftp_client

    def get_sftp_client(self) -> SFTPClient:
        """
        Getter for sftp_client.
        """
        return self.sftp_client

    def set_destination_path(self, destination_path: str):
        """
        Setter for destination_path.
        """
        self.destination_path = destination_path

    def get_destination_path(self) -> str:
        """
        Getter for destination_path.
        """
        return self.destination_path

    def set_origin_path(self, origin_path: str):
        """
        Setter for origin_path.
        """
        self.origin_path = origin_path

    def get_origin_path(self) -> str:
        """
        Getter for origin_path.
        """
        return self.origin_path

    def set_transfer_direction(self, transfer_direction: TransferDirection):
        """
        Setter for transfer_direction.
        """
        self.transfer_direction = transfer_direction

    def get_transfer_direction(self) -> TransferDirection:
        """
        Getter for transfer_direction.
        """
        return self.transfer_direction

    def set_timeout_in_seconds(self, timeout_in_seconds: int):
        """
        Setter for timeout_in_seconds.
        """
        self.timeout_in_seconds = timeout_in_seconds

    def get_timeout_in_seconds(self) -> int:
        """
        Getter for timeout_in_seconds.
        """
        return self.timeout_in_seconds

    def set_force(self, force: int):
        """
        Setter for force.
        If True, forces the transfer even if the file already exists in the destination.
        """
        self.force = force

    def get_force(self) -> int:
        """
        Getter for force.
        If True, forces the transfer even if the file already exists in the destination.
        """
        return self.force

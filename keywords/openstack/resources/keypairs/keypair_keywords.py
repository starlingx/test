"""Keypair CRUD keywords via OpenStack SDK."""

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.keypairs.object.keypair_list_output import KeypairListOutput


class KeypairKeywords(BaseKeyword):
    """CRUD operations for Nova keypairs via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize KeypairKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_keypairs(self) -> KeypairListOutput:
        """List all keypairs.

        Returns:
            KeypairListOutput: Parsed keypair collection.
        """
        raw_keypairs = [k.to_dict() for k in self.openstack_connection.get_compute().keypairs()]
        return KeypairListOutput(raw_keypairs)

    def create_keypair(self, keypair_name: str) -> KeypairListOutput:
        """Create a keypair.

        Args:
            keypair_name (str): Keypair name.

        Returns:
            KeypairListOutput: Parsed output containing the created keypair.
        """
        get_logger().log_info(f"Creating keypair '{keypair_name}'")
        kp = self.openstack_connection.get_compute().create_keypair(name=keypair_name)
        return KeypairListOutput([kp.to_dict()])

    def delete_keypair(self, keypair_name: str) -> None:
        """Delete a keypair.

        Args:
            keypair_name (str): Keypair name.
        """
        get_logger().log_info(f"Deleting keypair '{keypair_name}'")
        compute = self.openstack_connection.get_compute()
        kp = compute.find_keypair(keypair_name, ignore_missing=False)
        compute.delete_keypair(kp)

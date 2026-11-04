"""Collect independent host interface inventory through checked commands."""

from shlex import quote

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.ip.ip_keywords import IPKeywords
from keywords.linux.ip.object.host_interface_inventory_output import HostInterfaceInventoryOutput


class HostInterfaceInventoryKeywords(BaseKeyword):
    """Join ip link details with sysfs PF/VF identity mappings."""

    def __init__(self, ssh_connection: SSHConnection):
        """Use the supplied node connection.

        Args:
            ssh_connection (SSHConnection): Connection to the inventory node.
        """
        self.ssh_connection = ssh_connection

    def get_interface_inventory(self) -> HostInterfaceInventoryOutput:
        """Collect eligible interfaces and resolve their device links.

        Returns:
            HostInterfaceInventoryOutput: Independently collected interface identities.
        """
        inventory = IPKeywords(self.ssh_connection).get_host_interface_links()
        for name in inventory.get_interface_names():
            device = quote(f"/sys/class/net/{name}/device")
            command = f"if test -e {device}; then readlink -f {device} && find -H {device} -maxdepth 1 -name 'virtfn*' -printf '%f ' -exec readlink -f {{}} \\;; fi"
            output = self.ssh_connection.send(command)
            self.validate_success_return_code(self.ssh_connection)
            inventory.set_device_paths(name, output)
        return inventory

from typing import Union

from keywords.cloud_platform.system.kube_rootca.objects.system_kube_rootca_host_update_object import SystemKubeRootcaHostUpdateObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemKubeRootcaHostUpdateListOutput:
    """Parser for system kube-rootca-host-update-list output."""

    def __init__(self, command_output: Union[str, list[str]]):
        """Initialize parser with command output.

        Args:
            command_output (Union[str, list[str]]): Raw command output.
        """
        self.raw_output = command_output
        self.host_updates = self._parse_output(command_output)

    def _parse_output(self, output: Union[str, list[str]]) -> list[SystemKubeRootcaHostUpdateObject]:
        """Parse command output into list of host update objects.

        Args:
            output (Union[str, list[str]]): Command output to parse.

        Returns:
            list[SystemKubeRootcaHostUpdateObject]: List of host update objects.
        """
        parser = SystemTableParser(output)
        output_list = parser.get_output_values_list()

        host_updates = []
        for item in output_list:
            host_update = SystemKubeRootcaHostUpdateObject()
            host_update.set_hostname(item.get("hostname", ""))
            host_update.set_personality(item.get("personality", ""))
            host_update.set_state(item.get("state", ""))
            host_update.set_effective_rootca_cert(item.get("effective_rootca_cert", ""))
            host_update.set_target_rootca_cert(item.get("target_rootca_cert", ""))
            host_updates.append(host_update)
        return host_updates

    def get_host_updates(self) -> list[SystemKubeRootcaHostUpdateObject]:
        """Get list of host update objects.

        Returns:
            list[SystemKubeRootcaHostUpdateObject]: List of host updates.
        """
        return self.host_updates

    def get_host_update(self, hostname: str) -> SystemKubeRootcaHostUpdateObject:
        """Get host update by hostname.

        Args:
            hostname (str): Hostname to search for.

        Returns:
            SystemKubeRootcaHostUpdateObject: Host update object or None.
        """
        for host_update in self.host_updates:
            if host_update.get_hostname() == hostname:
                return host_update
        return None

from typing import Union

from keywords.cloud_platform.system.kube_rootca.objects.system_kube_rootca_update_object import SystemKubeRootcaUpdateObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemKubeRootcaUpdateVerticalOutput:
    """Parser for vertical table format kube-rootca-update output."""

    def __init__(self, command_output: Union[str, list[str]]):
        """Initialize parser with command output.

        Args:
            command_output (Union[str, list[str]]): Raw command output.
        """
        self.raw_output = command_output
        self.kube_rootca_update = self._parse_output(command_output)

    def _parse_output(self, output: Union[str, list[str]]) -> SystemKubeRootcaUpdateObject:
        """Parse command output into kube rootca update object.

        Args:
            output (Union[str, list[str]]): Command output to parse.

        Returns:
            SystemKubeRootcaUpdateObject: Parsed update object.
        """
        parser = SystemVerticalTableParser(output)
        output_dict = parser.get_output_values_dict()

        kube_rootca_update = SystemKubeRootcaUpdateObject()
        kube_rootca_update.set_uuid(output_dict.get("uuid", ""))
        kube_rootca_update.set_state(output_dict.get("state", ""))
        kube_rootca_update.set_from_rootca_cert(output_dict.get("from_rootca_cert", ""))
        kube_rootca_update.set_to_rootca_cert(output_dict.get("to_rootca_cert", ""))
        kube_rootca_update.set_created_at(output_dict.get("created_at", ""))
        kube_rootca_update.set_updated_at(output_dict.get("updated_at", ""))
        return kube_rootca_update

    def get_kube_rootca_update(self) -> SystemKubeRootcaUpdateObject:
        """Get kube rootca update object.

        Returns:
            SystemKubeRootcaUpdateObject: Update object.
        """
        return self.kube_rootca_update

from keywords.cloud_platform.system.kubernetes.object.kube_host_upgrade_object import KubeHostUpgradeObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class KubeHostUpgradeOutput:
    """Parses the output of 'system kube-host-upgrade' commands into a KubeHostUpgradeObject.

    This output format is shared by both 'system kube-host-upgrade {host} control-plane'
    and 'system kube-host-upgrade {host} kubelet'.
    """

    def __init__(self, kube_host_upgrade_output: list) -> None:
        """Constructor.

        Args:
            kube_host_upgrade_output (list): Raw output of a kube-host-upgrade command.
        """
        parser = SystemVerticalTableParser(kube_host_upgrade_output)
        output_values = parser.get_output_values_dict()

        self.kube_host_upgrade_object = KubeHostUpgradeObject()
        self.kube_host_upgrade_object.set_control_plane_version(output_values["control_plane_version"])
        self.kube_host_upgrade_object.set_hostname(output_values["hostname"])
        self.kube_host_upgrade_object.set_id(output_values["id"])
        self.kube_host_upgrade_object.set_kubelet_version(output_values["kubelet_version"])
        self.kube_host_upgrade_object.set_personality(output_values["personality"])
        self.kube_host_upgrade_object.set_status(output_values["status"])
        self.kube_host_upgrade_object.set_target_version(output_values["target_version"])

    def get_kube_host_upgrade_object(self) -> KubeHostUpgradeObject:
        """Retrieves the parsed kube host upgrade object.

        Returns:
            KubeHostUpgradeObject: The parsed kube-host-upgrade object.
        """
        return self.kube_host_upgrade_object

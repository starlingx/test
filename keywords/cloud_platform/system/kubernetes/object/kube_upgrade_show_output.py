from keywords.cloud_platform.system.kubernetes.object.kube_upgrade_show_object import KubeUpgradeShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class KubeUpgradeShowOutput:
    """Parses the output of 'system kube-upgrade-show' and related commands into a KubeUpgradeShowObject.

    This output format is shared by: kube-upgrade-show, kube-upgrade-start,
    kube-upgrade-download-images, kube-pre-application-update,
    kube-post-application-update, kube-upgrade-networking, kube-upgrade-storage,
    kube-host-cordon, kube-host-uncordon, kube-host-upgrade, kube-upgrade-complete and kube-upgrade-abort.
    """

    def __init__(self, kube_upgrade_show_output: list) -> None:
        """Constructor.

        Args:
            kube_upgrade_show_output (list): Raw output of a kube-upgrade command.
        """
        parser = SystemVerticalTableParser(kube_upgrade_show_output)
        output_values = parser.get_output_values_dict()

        self.kube_upgrade_show_object = KubeUpgradeShowObject()
        self.kube_upgrade_show_object.set_uuid(output_values["uuid"])
        self.kube_upgrade_show_object.set_from_version(output_values["from_version"])
        self.kube_upgrade_show_object.set_to_version(output_values["to_version"])
        self.kube_upgrade_show_object.set_state(output_values["state"])
        self.kube_upgrade_show_object.set_created_at(output_values["created_at"])
        self.kube_upgrade_show_object.set_updated_at(output_values["updated_at"])

    def get_kube_upgrade_show_object(self) -> KubeUpgradeShowObject:
        """Retrieves the parsed kubernetes upgrade object.

        Returns:
            KubeUpgradeShowObject: The parsed kube-upgrade-show object.
        """
        return self.kube_upgrade_show_object

from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_show_object import DcManagerSubcloudDeployShowObject


class DcManagerSubcloudDeployShowOutput:
    """Represents the output of 'dcmanager subcloud deploy show' command as DcManagerSubcloudDeployShowObject object."""

    def __init__(self, dcmanager_subcloud_deploy_show_output: list[str]) -> None:
        """Constructor.

        Args:
            dcmanager_subcloud_deploy_show_output (list[str]): The output of 'dcmanager subcloud deploy show' command.
        """
        self.dcmanager_subcloud_deploy_show_object: DcManagerSubcloudDeployShowObject
        dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_deploy_show_output)
        output_values = dcmanager_vertical_table_parser.get_output_values_dict()

        dcmanager_subcloud_deploy_show_object = DcManagerSubcloudDeployShowObject()

        if "deploy_playbook" in output_values:
            dcmanager_subcloud_deploy_show_object.set_deploy_playbook(output_values["deploy_playbook"])

        if "deploy_overrides" in output_values:
            dcmanager_subcloud_deploy_show_object.set_deploy_overrides(output_values["deploy_overrides"])

        if "deploy_chart" in output_values:
            dcmanager_subcloud_deploy_show_object.set_deploy_chart(output_values["deploy_chart"])

        if "prestage_images" in output_values:
            dcmanager_subcloud_deploy_show_object.set_prestage_images(output_values["prestage_images"])

        if "software_version" in output_values:
            dcmanager_subcloud_deploy_show_object.set_software_version(output_values["software_version"])

        self.dcmanager_subcloud_deploy_show_object = dcmanager_subcloud_deploy_show_object

    def get_dcmanager_subcloud_deploy_show_object(self) -> DcManagerSubcloudDeployShowObject:
        """Get the DcManagerSubcloudDeployShowObject.

        Returns:
            DcManagerSubcloudDeployShowObject: The DcManagerSubcloudDeployShowObject object representing the
            output of the command 'dcmanager subcloud deploy show'.
        """
        return self.dcmanager_subcloud_deploy_show_object

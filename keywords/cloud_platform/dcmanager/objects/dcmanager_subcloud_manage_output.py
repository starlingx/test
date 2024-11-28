from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_manage_object import DcManagerSubcloudManageObject


class DcManagerSubcloudManageOutput:
    """
    Responsible to populate an object with the data provided by the output of
    'dcmanager subcloud <manage/unmanage> <subcloud name>' command and provides a way to access this object.

    """

    def __init__(self, dcmanager_subcloud_manage_output: str):
        """
        Constructor

        Args:
            dcmanager_subcloud_manage_output (str): output of 'dcmanager subcloud <manage/unmanage> <subcloud name>'
            command.

        """
        dcmanager_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_manage_output)
        output_values = dcmanager_table_parser.get_output_values_dict()
        dcmanager_subcloud_manage_object = DcManagerSubcloudManageObject()

        dcmanager_subcloud_manage_object.set_name(output_values.get('id'))
        dcmanager_subcloud_manage_object.set_name(output_values.get('name'))
        dcmanager_subcloud_manage_object.set_description(output_values.get('description'))
        dcmanager_subcloud_manage_object.set_location(output_values.get('location'))
        dcmanager_subcloud_manage_object.set_software_version(output_values.get('software_version'))
        dcmanager_subcloud_manage_object.set_management(output_values.get('management'))
        dcmanager_subcloud_manage_object.set_availability(output_values.get('availability'))
        dcmanager_subcloud_manage_object.set_deploy_status(output_values.get('deploy_status'))
        dcmanager_subcloud_manage_object.set_management_subnet(output_values.get('management_subnet'))
        dcmanager_subcloud_manage_object.set_management_start_ip(output_values.get('management_start_ip'))
        dcmanager_subcloud_manage_object.set_management_end_ip(output_values.get('management_end_ip'))
        dcmanager_subcloud_manage_object.set_management_gateway_ip(output_values.get('management_gateway_ip'))
        dcmanager_subcloud_manage_object.set_systemcontroller_gateway_ip(output_values.get('systemcontroller_gateway_ip'))
        dcmanager_subcloud_manage_object.set_group_id(output_values.get('group_id'))
        dcmanager_subcloud_manage_object.set_peer_group_id(output_values.get('peer_group_id'))
        dcmanager_subcloud_manage_object.set_created_at(output_values.get('created_at'))
        dcmanager_subcloud_manage_object.set_updated_at(output_values.get('updated_at'))
        dcmanager_subcloud_manage_object.set_backup_status(output_values.get('backup_status'))
        dcmanager_subcloud_manage_object.set_backup_datetime(output_values.get('backup_datetime'))
        dcmanager_subcloud_manage_object.set_prestage_status(output_values.get('prestage_status'))
        dcmanager_subcloud_manage_object.set_prestage_versions(output_values.get('prestage_versions'))

        self.dcmanager_subcloud_manage_object = dcmanager_subcloud_manage_object

    def get_dcmanager_subcloud_manage_object(self) -> DcManagerSubcloudManageObject:
        """
        This function will return the DcManagerSubcloudManageObject instance representing the output of
        'dcmanager subcloud <manage/unmanage> <subcloud name>' command.

        Args: None

        Returns:
            DcManagerSubcloudManageObject: an instance of DcManagerSubcloudManageObject representing the output
             of 'dcmanager subcloud <manage/unmanage> <subcloud name>' command.

        """
        return self.dcmanager_subcloud_manage_object

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_object import DcManagerSubcloudShowObject


class DcManagerSubcloudShowOutput:
    """
    Represents the output of 'dcmanager subcloud show <subcloud>' command as DcManagerSubcloudListObject object.
    """

    def __init__(self, dcmanager_subcloud_show_output: list[str]) -> None:
        """
        Constructor

        Args:
            dcmanager_subcloud_show_output (list[str]): the output of 'dcmanager subcloud show <subcloud>' command
        """
        self.dcmanager_subcloud_show_object: DcManagerSubcloudShowObject
        dcmanager_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_subcloud_show_output)
        output_values = dcmanager_vertical_table_parser.get_output_values_dict()

        if "id" not in output_values:
            raise KeywordException(f"The output {dcmanager_subcloud_show_output} was not valid because it is missing an 'id'.")

        dcmanager_subcloud_show_object = DcManagerSubcloudShowObject(output_values.get("id"))

        dcmanager_subcloud_show_object.set_name(output_values.get("name"))
        dcmanager_subcloud_show_object.set_description(output_values.get("description"))
        dcmanager_subcloud_show_object.set_location(output_values.get("location"))
        dcmanager_subcloud_show_object.set_software_version(output_values.get("software_version"))
        dcmanager_subcloud_show_object.set_management(output_values.get("management"))
        dcmanager_subcloud_show_object.set_availability(output_values.get("availability"))
        dcmanager_subcloud_show_object.set_deploy_status(output_values.get("deploy_status"))
        dcmanager_subcloud_show_object.set_management_subnet(output_values.get("management_subnet"))
        dcmanager_subcloud_show_object.set_management_start_ip(output_values.get("management_start_ip"))
        dcmanager_subcloud_show_object.set_management_end_ip(output_values.get("management_end_ip"))
        dcmanager_subcloud_show_object.set_management_gateway_ip(output_values.get("management_gateway_ip"))
        dcmanager_subcloud_show_object.set_systemcontroller_gateway_ip(output_values.get("systemcontroller_gateway_ip"))
        dcmanager_subcloud_show_object.set_group_id(output_values.get("group_id"))
        dcmanager_subcloud_show_object.set_peer_group_id(output_values.get("peer_group_id"))
        dcmanager_subcloud_show_object.set_created_at(output_values.get("created_at"))
        dcmanager_subcloud_show_object.set_updated_at(output_values.get("updated_at"))
        dcmanager_subcloud_show_object.set_backup_status(output_values.get("backup_status"))
        dcmanager_subcloud_show_object.set_backup_datetime(output_values.get("backup_datetime"))
        dcmanager_subcloud_show_object.set_prestage_status(output_values.get("prestage_status"))
        dcmanager_subcloud_show_object.set_prestage_versions(output_values.get("prestage_versions"))
        dcmanager_subcloud_show_object.set_dc_cert_sync_status(output_values.get("dc-cert_sync_status"))
        dcmanager_subcloud_show_object.set_firmware_sync_status(output_values.get("firmware_sync_status"))
        dcmanager_subcloud_show_object.set_identity_sync_status(output_values.get("identity_sync_status"))
        dcmanager_subcloud_show_object.set_kubernetes_sync_status(output_values.get("kubernetes_sync_status"))
        dcmanager_subcloud_show_object.set_kube_rootca_sync_status(output_values.get("kube-rootca_sync_status"))
        dcmanager_subcloud_show_object.set_load_sync_status(output_values.get("load_sync_status"))
        dcmanager_subcloud_show_object.set_patching_sync_status(output_values.get("patching_sync_status"))
        dcmanager_subcloud_show_object.set_platform_sync_status(output_values.get("platform_sync_status"))
        dcmanager_subcloud_show_object.set_usm_sync_status(output_values.get("usm_sync_status"))
        dcmanager_subcloud_show_object.set_region_name(output_values.get("region_name"))
        dcmanager_subcloud_show_object.set_software_sync_status(output_values.get("software_sync_status"))

        self.dcmanager_subcloud_show_object = dcmanager_subcloud_show_object

    def get_dcmanager_subcloud_show_object(self) -> DcManagerSubcloudShowObject:
        """DcManagerSubcloudShowObject.

        Returns:
            DcManagerSubcloudShowObject: the DcManagerSubcloudShowObject object representing the
            output of the command 'dcmanager subcloud show <subcloud>'.
        """
        return self.dcmanager_subcloud_show_object

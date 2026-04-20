"""OpenStack volume type list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser
from keywords.cloud_platform.openstack.volume.object.openstack_volume_type_list_object import OpenStackVolumeTypeListObject


class OpenStackVolumeTypeListOutput:
    """Class for openstack volume type list output."""

    def __init__(self, openstack_volume_type_list_output):
        """Initialize OpenStackVolumeTypeListOutput.

        Args:
            openstack_volume_type_list_output: Raw CLI output to parse.
        """
        self.openstack_volume_type_list_objects: list[OpenStackVolumeTypeListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_volume_type_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            volume_type_object = OpenStackVolumeTypeListObject()
            volume_type_object.set_id(value["ID"])
            volume_type_object.set_name(value["Name"])
            volume_type_object.set_is_public(value["Is Public"])

            self.openstack_volume_type_list_objects.append(volume_type_object)

    def get_volume_types(self) -> list[OpenStackVolumeTypeListObject]:
        """Get the list of volume type objects.

        Returns:
            list[OpenStackVolumeTypeListObject]: List of volume type objects.
        """
        return self.openstack_volume_type_list_objects

    def get_volume_type_by_name(self, name: str) -> OpenStackVolumeTypeListObject:
        """Get the volume type with the given name.

        Args:
            name (str): Volume type name.

        Returns:
            OpenStackVolumeTypeListObject: The volume type object with the given name.

        Raises:
            KeywordException: If no volume type is found with the given name.
        """
        for volume_type in self.openstack_volume_type_list_objects:
            if volume_type.get_name() == name:
                return volume_type
        raise KeywordException(f"No volume type was found with name {name}")

    def get_volume_type_by_id(self, volume_type_id: str) -> OpenStackVolumeTypeListObject:
        """Get the volume type with the given id.

        Args:
            volume_type_id (str): Volume type id.

        Returns:
            OpenStackVolumeTypeListObject: The volume type object with the given id.

        Raises:
            KeywordException: If no volume type is found with the given id.
        """
        for volume_type in self.openstack_volume_type_list_objects:
            if volume_type.get_id() == volume_type_id:
                return volume_type
        raise KeywordException(f"No volume type was found with id {volume_type_id}")

    def is_volume_type(self, name: str) -> bool:
        """Check if a volume type with the given name exists.

        Args:
            name (str): Volume type name.

        Returns:
            bool: True if the volume type exists, False otherwise.
        """
        for volume_type in self.openstack_volume_type_list_objects:
            if volume_type.get_name() == name:
                return True
        return False

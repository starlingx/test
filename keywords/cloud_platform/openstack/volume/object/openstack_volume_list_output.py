"""OpenStack volume list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser
from keywords.cloud_platform.openstack.volume.object.openstack_volume_list_object import OpenStackVolumeListObject


class OpenStackVolumeListOutput:
    """Class for openstack volume list output."""

    def __init__(self, openstack_volume_list_output):
        """Initialize OpenStackVolumeListOutput.

        Args:
            openstack_volume_list_output: Raw CLI output to parse.
        """
        self.openstack_volume_list_objects: list[OpenStackVolumeListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_volume_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            volume_object = OpenStackVolumeListObject()
            volume_object.set_id(value["ID"])
            volume_object.set_name(value["Name"])
            volume_object.set_status(value["Status"])
            volume_object.set_size(value["Size"])
            volume_object.set_attached_to(value["Attached to"])

            self.openstack_volume_list_objects.append(volume_object)

    def get_volumes(self) -> list[OpenStackVolumeListObject]:
        """Get the list of volume objects.

        Returns:
            list[OpenStackVolumeListObject]: List of volume objects.
        """
        return self.openstack_volume_list_objects

    def get_volume_by_name(self, name: str) -> OpenStackVolumeListObject:
        """Get the volume with the given name.

        Args:
            name (str): Volume name.

        Returns:
            OpenStackVolumeListObject: The volume object with the given name.

        Raises:
            KeywordException: If no volume is found with the given name.
        """
        for volume in self.openstack_volume_list_objects:
            if volume.get_name() == name:
                return volume
        raise KeywordException(f"No volume was found with name {name}")

    def get_volume_by_id(self, volume_id: str) -> OpenStackVolumeListObject:
        """Get the volume with the given id.

        Args:
            volume_id (str): Volume id.

        Returns:
            OpenStackVolumeListObject: The volume object with the given id.

        Raises:
            KeywordException: If no volume is found with the given id.
        """
        for volume in self.openstack_volume_list_objects:
            if volume.get_id() == volume_id:
                return volume
        raise KeywordException(f"No volume was found with id {volume_id}")

    def get_volumes_by_status(self, status: str) -> list[OpenStackVolumeListObject]:
        """Get all volumes with the given status.

        Args:
            status (str): Volume status (e.g. 'available', 'in-use', 'error').

        Returns:
            list[OpenStackVolumeListObject]: List of volumes with the given status.
        """
        return [volume for volume in self.openstack_volume_list_objects if volume.get_status() == status]

    def get_total_size_gb(self) -> int:
        """Get the total size of all volumes in GB.

        Returns:
            int: Total size of all volumes in GB.
        """
        return sum(volume.get_size_as_int() for volume in self.openstack_volume_list_objects)

    def is_volume(self, name: str) -> bool:
        """Check if a volume with the given name exists.

        Args:
            name (str): Volume name.

        Returns:
            bool: True if the volume exists, False otherwise.
        """
        for volume in self.openstack_volume_list_objects:
            if volume.get_name() == name:
                return True
        return False

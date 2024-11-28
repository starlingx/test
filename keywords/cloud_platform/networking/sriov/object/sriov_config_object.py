from keywords.cloud_platform.system.host.objects.system_host_interface_object import SystemHostInterfaceObject
from keywords.cloud_platform.system.interface.objects.system_interface_datanetwork_object import SystemInterfaceDatanetworkObject


class SriovConfigObject:
    """
    Class for Sriov Config
    """

    def __init__(self, system_host_interface_object: SystemHostInterfaceObject, datanetworks: SystemInterfaceDatanetworkObject):

        self.system_host_interface_object = system_host_interface_object
        self.datanetworks: SystemInterfaceDatanetworkObject = datanetworks

    def set_system_host_interface_object(self, system_host_interface_object: SystemHostInterfaceObject):
        """
        Setter for name
        Args:
            system_host_interface_object (): the system_host_interface_object

        Returns:

        """
        self.system_host_interface_object = system_host_interface_object

    def get_system_host_interface_object(self) -> SystemHostInterfaceObject:
        """
        Getter for system_host_interface_object
        Returns:

        """
        return self.system_host_interface_object

    def set_datanetworks(self, datanetworks: SystemInterfaceDatanetworkObject):
        """
        Setter for datanetworks
        Args:
            datanetworks (): the datanetworks

        Returns:

        """
        self.datanetworks = datanetworks

    def get_datanetworks(self) -> SystemInterfaceDatanetworkObject:
        """
        Getter for datanetworks
        Returns:

        """
        return self.datanetworks

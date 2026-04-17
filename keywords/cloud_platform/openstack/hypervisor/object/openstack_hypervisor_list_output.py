"""OpenStack hypervisor list output parsing."""

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.hypervisor.object.openstack_hypervisor_list_object import OpenStackHypervisorListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackHypervisorListOutput:
    """Class for openstack hypervisor list output."""

    def __init__(self, openstack_hypervisor_list_output):
        """Initialize OpenStackHypervisorListOutput.

        Args:
            openstack_hypervisor_list_output: Raw CLI output to parse.
        """
        self.openstack_hypervisor_list_objects: [OpenStackHypervisorListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_hypervisor_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            hypervisor_object = OpenStackHypervisorListObject()
            hypervisor_object.set_id(value["ID"])
            hypervisor_object.set_hypervisor_hostname(value["Hypervisor Hostname"])
            hypervisor_object.set_hypervisor_type(value["Hypervisor Type"])
            hypervisor_object.set_host_ip(value["Host IP"])
            hypervisor_object.set_state(value["State"])

            self.openstack_hypervisor_list_objects.append(hypervisor_object)

    def get_hypervisors(self) -> [OpenStackHypervisorListObject]:
        """Get the list of hypervisor objects.

        Returns:
            list[OpenStackHypervisorListObject]: List of hypervisor objects.
        """
        return self.openstack_hypervisor_list_objects

    def get_hypervisor_by_hostname(self, hostname: str) -> OpenStackHypervisorListObject:
        """Get the hypervisor with the given hostname.

        Args:
            hostname (str): hypervisor hostname.

        Returns:
            OpenStackHypervisorListObject: The hypervisor object with the given hostname.
        """
        for hypervisor in self.openstack_hypervisor_list_objects:
            if hypervisor.get_hypervisor_hostname() == hostname:
                return hypervisor
        raise KeywordException(f"No hypervisor was found with hostname {hostname}")

    def is_hypervisor(self, hostname: str) -> bool:
        """Check if a hypervisor with the given hostname exists.

        Args:
            hostname (str): hypervisor hostname.

        Returns:
            bool: True if the hypervisor exists, False otherwise.
        """
        for hypervisor in self.openstack_hypervisor_list_objects:
            if hypervisor.get_hypervisor_hostname() == hostname:
                return True
        return False

from framework.exceptions.keyword_exception import KeywordException
from keywords.cloud_platform.openstack.endpoint.objects.openstack_endpoint_list_object import OpenStackEndpointListObject
from keywords.cloud_platform.openstack.openstack_table_parser import OpenStackTableParser


class OpenStackEndpointListOutput:
    """
    Class for open stack endpoint output
    """

    def __init__(self, openstack_endpoint_list_output):
        self.openstack_endpoint_list_objects: [OpenStackEndpointListObject] = []
        openstack_table_parser = OpenStackTableParser(openstack_endpoint_list_output)
        output_values = openstack_table_parser.get_output_values_list()

        for value in output_values:
            endpoint_object = OpenStackEndpointListObject()
            endpoint_object.set_id(value['ID'])
            endpoint_object.set_region(value['Region'])
            endpoint_object.set_service_name(value['Service Name'])
            endpoint_object.set_service_type(value['Service Type'])
            endpoint_object.set_enabled(value['Enabled'])
            endpoint_object.set_interface(value['Interface'])
            endpoint_object.set_url(value['URL'])

            self.openstack_endpoint_list_objects.append(endpoint_object)

    def get_endpoints(self) -> [OpenStackEndpointListObject]:
        """
        Getter for endpoints
        Returns:

        """
        return self.openstack_endpoint_list_objects

    def is_endpoint(self, service_name: str) -> bool:
        """
        This function will return true if the 'service_name' endpoint exists in the list.
        Args:
            service_name: Name of the service that we are looking for.

        Returns: Boolean

        """
        for endpoint in self.openstack_endpoint_list_objects:
            if endpoint.get_service_name() == service_name:
                return True
        return False

    def get_endpoint(self, service_name: str, interface) -> OpenStackEndpointListObject:
        """
        Gets the endpoint with the given service and interface
        Args:
            service_name (): service name
            interface (): interface

        Returns:

        """

        endpoints = list(filter(lambda endpoint: endpoint.get_service_name() == service_name and endpoint.get_interface() == interface, self.openstack_endpoint_list_objects))

        if len(endpoints) < 1:
            raise KeywordException(f"No endpoint was found with service name {service_name} and interface {interface}")

        return endpoints[0]

    def get_horizon_url(self):
        """
        Gets the Horizon Endpoint URL for this lab.
        Args:
            ssh_connection: Connection to the active controller.

        Returns:

        """
        # Remove port from orignal url and then add 8443 for https or 8080 for http
        url = self.get_endpoint('keystone', 'public').get_url().rsplit(':', 1)[0]
        if 'https' in url:
            url += ':8443/'
        else:
            url += ':8080/'

        return url

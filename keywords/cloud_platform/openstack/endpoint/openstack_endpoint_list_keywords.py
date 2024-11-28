from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.openstack.endpoint.objects.openstack_endpoint_list_output import OpenStackEndpointListOutput


class OpenStackEndpointListKeywords(BaseKeyword):
    """
    Class for OpenStack Endpoint list keywords
    """

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def endpoint_list(self):
        """
        Keyword for openstack endpoint list
        Returns:

        """
        output = self.ssh_connection.send(source_openrc('openstack endpoint list'))
        self.validate_success_return_code(self.ssh_connection)
        openstack_endpoint_list_output = OpenStackEndpointListOutput(output)

        return openstack_endpoint_list_output

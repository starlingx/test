from config.configuration_manager import ConfigurationManager
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
            OpenStackEndpointListOutput object
        """
        output = self.ssh_connection.send(source_openrc("openstack endpoint list"))
        self.validate_success_return_code(self.ssh_connection)
        openstack_endpoint_list_output = OpenStackEndpointListOutput(output)

        return openstack_endpoint_list_output

    def get_k8s_dashboard_url(self) -> str:
        """
        Getter for the URL of the K8s dashboard.
        """
        endpoint_output = self.endpoint_list()
        url = endpoint_output.get_endpoint("keystone", "public").get_url().rsplit(":", 1)[0]
        end_point = f"{url}:{ConfigurationManager.get_k8s_config().get_dashboard_port()}"
        return end_point

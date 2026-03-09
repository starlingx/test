from framework.validation.validation import validate_equals_with_retry

from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_show_output import DcManagerSubcloudShowOutput
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_network_object import DcManagerSubcloudNetworkObject
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords


class DcManagerSubcloudUpdateKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud update' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection(SSHConnection): An active SSH connection to the controller.

        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_update(self, subcloud_name: str, update_attr: str, update_value: str) -> DcManagerSubcloudShowOutput:
        """
        Updates the subcloud attr using'dcmanager subcloud update <subcloud name> --<update_attr> <update_value>' output.

        Args:
            subcloud_name (str): a str representing a subcloud's name.
            update_attr (str): the attribute to update (ex. description)
            update_value (str): the value to update the attribute to (ex. this is a new description)

        Returns:
            DcManagerSubcloudShowOutput: Object representation of the command output.

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud update {subcloud_name} --{update_attr} '{update_value}'"))
        self.validate_success_return_code(self.ssh_connection)
        dcmanager_subcloud_show_output = DcManagerSubcloudShowOutput(output)

        return dcmanager_subcloud_show_output

    def dcmanager_subcloud_update_network(self, subcloud_name: str, network_attr: DcManagerSubcloudNetworkObject) -> None:
        """
        Updates the subcloud network configuration using 'dcmanager subcloud update' command.

        Args:
            subcloud_name (str): a str representing a subcloud's name.
            network_attr (DcManagerSubcloudNetworkObject): Network configuration object.

        Returns:
            None

        """

        cmd = (f"dcmanager subcloud update "
               f"--management-subnet {network_attr.get_management_subnet()} "
               f" --management-gateway-ip {network_attr.get_management_gateway_address()} "
               f" --management-start-ip {network_attr.get_management_start_address()} "
               f" --management-end-ip {network_attr.get_management_end_address()} "
               f" --bootstrap-address {network_attr.get_bootstrap_address()} "
               f" {subcloud_name}"
               f" --sysadmin-password {network_attr.get_sysadmin_password()} ")

        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        self.wait_for_subcloud_update_network(subcloud_name)

    def wait_for_subcloud_update_network(
        self,
        subcloud: str,
        check_interval: int = 60,
        timeout: int = 3600,
    ) -> None:

        def check_network_updated() -> str:
            """
            Checks if restore has been completed.

            Returns:
                str: A message indicating whether the backup has been successfully created or not.
            """
            dcmanager_subcloud_show_obj = DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud).get_dcmanager_subcloud_show_object()
            deploy_status = dcmanager_subcloud_show_obj.get_deploy_status()
            availability = dcmanager_subcloud_show_obj.get_availability()

            if deploy_status == "complete" and availability == "online":
                return f"{subcloud} network reconfig complete."
            elif deploy_status == "network-reconfiguration-failed":
                return f"{subcloud} network reconfiguration failed."
            else:
                return "Restore not done yet."

        validate_equals_with_retry(
            function_to_execute=check_network_updated,
            expected_value=f"{subcloud} network reconfig complete.",
            validation_description=f"Network update for {subcloud} completed.",
            timeout=timeout,
            polling_sleep_time=check_interval,
            failure_values=[f"{subcloud} network update failed."]
        )

    def dcmanager_subcloud_update_with_error(self, subcloud_name: str, update_attr: str, update_value: str) -> str:
        """
        Updates the subcloud attr using'dcmanager subcloud update <subcloud name> --<update_attr> <update_value>' output(error handling version).

        Args:
            subcloud_name (str): a str representing a subcloud's name.
            update_attr (str): the attribute to update (ex. description)
            update_value (str): the value to update the attribute to (ex. this is a new description)

        Returns:
            str: Raw command output (for error validation).

        """
        output = self.ssh_connection.send(source_openrc(f"dcmanager subcloud update {subcloud_name} --{update_attr} '{update_value}'"))
        if isinstance(output, list) and len(output) > 0:
            return "\n".join(line.strip() for line in output)
        return output.strip() if isinstance(output, str) else str(output)

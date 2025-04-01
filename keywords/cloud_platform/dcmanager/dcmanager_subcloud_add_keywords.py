from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords


class DcManagerSubcloudAddKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud Add' commands.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor

        Args:
            ssh_connection (SSHConnection): ssh for the active controller
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_add(self, subcloud_name: str):
        """Adds the subcloud using 'dcmanager subcloud add '.

        Args:
            subcloud_name (str): a str name for the subcloud.

        """
        # Get the subcloud config
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)

        # Get the subcloud deployment assets
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        bootstrap_file = sc_assets.get_bootstrap_file()
        deploy_file = sc_assets.get_deployment_config_file()
        install_file = sc_assets.get_install_file()

        # Get the subcloud bootstrap address
        boot_add = sc_config.get_nodes()[0].get_ip()
        admin_creds = sc_config.get_admin_credentials()

        # Execute the command
        cmd = f"dcmanager subcloud add --bootstrap-address {boot_add} --bootstrap-values {bootstrap_file} --deploy-config {deploy_file} --sysadmin-password {admin_creds.get_password()} --bmc-password {sc_config.get_bm_password()} --install-values {install_file}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
        dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, "complete")

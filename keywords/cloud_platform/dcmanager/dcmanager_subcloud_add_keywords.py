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

    def dcmanager_subcloud_add(self, subcloud_name: str, release_id: str = None):
        """Adds the subcloud using 'dcmanager subcloud add '.

        Args:
            subcloud_name (str): a str name for the subcloud.
            release_id (str): a str name for the release_id.

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
        boot_add = sc_config.get_first_controller().get_ip()
        admin_creds = sc_config.get_admin_credentials()
        release = "" if release_id is None else f"--release {release_id}"
        # Execute the command
        cmd = f"dcmanager subcloud add --bootstrap-address {boot_add} --bootstrap-values {bootstrap_file} --deploy-config {deploy_file} --sysadmin-password {admin_creds.get_password()} --bmc-password {sc_config.get_bm_password()} --install-values {install_file} {release}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
        dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, "complete")

    def dcmanager_subcloud_add_migrate(self, subcloud_name: str, bootstrap_values: str, install_values: str):
        """
        Runs 'dcmanager subcloud add --migrate' command.

        Args:
            subcloud_name (str): Subcloud name.
            bootstrap_values (str): Bootstrap values file name.
            install_values (str): Install values file name.
        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_obj = lab_config.get_subcloud(subcloud_name)

        subcloud_ip = subcloud_obj.get_floating_ip()
        subcloud_psswr = subcloud_obj.get_admin_credentials().get_password()

        cmd = source_openrc(f"dcmanager subcloud add --migrate --bootstrap-address {subcloud_ip} " f"--bootstrap-values {bootstrap_values} --install-values {install_values}" f" --sysadmin-password {subcloud_psswr} --bmc-password {subcloud_psswr}")

        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

    def dcmanager_subcloud_add_enroll(self, subcloud_name: str, bootstrap_values: str, install_values: str, deploy_config_file: str):
        """
        Runs 'dcmanager subcloud add --enroll' command.

        Args:
            subcloud_name (str): Subcloud name.
            bootstrap_values (str): Bootstrap values file name.
            install_values (str): Install values file name.
            deploy_config_file (str): Deployment config file name.
        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_obj = lab_config.get_subcloud(subcloud_name)

        subcloud_ip = subcloud_obj.get_floating_ip()
        subcloud_psswr = subcloud_obj.get_admin_credentials().get_password()

        cmd = source_openrc(f"dcmanager subcloud add --enroll --bootstrap-address {subcloud_ip} --bootstrap-values {bootstrap_values} --install-values {install_values} --deploy-config {deploy_config_file} --sysadmin-password {subcloud_psswr} --bmc-password {subcloud_psswr}")

        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

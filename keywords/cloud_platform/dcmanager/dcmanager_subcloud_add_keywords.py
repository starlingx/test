from typing import Optional

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

    def dcmanager_subcloud_add(self, subcloud_name: str, release_id: str = None, wait_for_status: bool = True):
        """Adds the subcloud using 'dcmanager subcloud add '.

        Args:
            subcloud_name (str): a str name for the subcloud.
            release_id (str): a str name for the release_id.
            wait_for_status (bool): whether to wait for deploy status to reach complete. Defaults to True.

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
        boot_add = sc_config.get_floating_ip()
        admin_creds = sc_config.get_admin_credentials()
        release = "" if release_id is None else f"--release {release_id}"
        # Execute the command
        cmd = f"dcmanager subcloud add --bootstrap-address {boot_add} --bootstrap-values {bootstrap_file} --deploy-config {deploy_file} --sysadmin-password {admin_creds.get_password()} --bmc-password {sc_config.get_bm_password()} --install-values {install_file} {release}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        if wait_for_status:
            dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, "complete")

    def dcmanager_subcloud_add_with_error(
        self,
        subcloud_name: str,
        bootstrap_values: str,
        enroll: bool = False,
        install_values: Optional[str] = None,
        deploy_config_file: Optional[str] = None,
        bmc_password: Optional[str] = None,
        cloud_init_config: Optional[str] = None,
    ) -> tuple:
        """Runs 'dcmanager subcloud add' and returns output and rc without asserting.

        Used for negative testing where the command is expected to be rejected.

        Args:
            subcloud_name (str): Subcloud name (used to look up IP and credentials).
            bootstrap_values (str): Bootstrap values file name.
            enroll (bool): Include --enroll flag. Defaults to False.
            install_values (Optional[str]): Install values file path. Defaults to None.
            deploy_config_file (Optional[str]): Deploy config file path. Defaults to None.
            bmc_password (Optional[str]): BMC password. Defaults to None.
            cloud_init_config (Optional[str]): Cloud-init config tarball path. Defaults to None.

        Returns:
            tuple: (output_str, return_code_int).
        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_obj = lab_config.get_subcloud(subcloud_name)
        subcloud_ip = subcloud_obj.get_floating_ip()
        subcloud_psswr = subcloud_obj.get_admin_credentials().get_password()
        cmd = f"dcmanager subcloud add --bootstrap-address {subcloud_ip} --bootstrap-values {bootstrap_values} --sysadmin-password {subcloud_psswr}"
        if enroll:
            cmd += " --enroll"
        if install_values:
            cmd += f" --install-values {install_values}"
        if deploy_config_file:
            cmd += f" --deploy-config {deploy_config_file}"
        if bmc_password:
            cmd += f" --bmc-password {bmc_password}"
        if cloud_init_config:
            cmd += f" --cloud-init-config {cloud_init_config}"
        output = self.ssh_connection.send(source_openrc(cmd))
        rc = self.ssh_connection.get_return_code()
        if isinstance(output, list):
            output = "\n".join(str(line).strip() for line in output)
        return output, rc

    def dcmanager_subcloud_add_migrate(self, subcloud_name: str, bootstrap_values: str, install_values: str, release_id: str = None):
        """
        Runs 'dcmanager subcloud add --migrate' command.

        Args:
            subcloud_name (str): Subcloud name.
            bootstrap_values (str): Bootstrap values file name.
            install_values (str): Install values file name.
            release_id (str): Release ID for the subcloud.
        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_obj = lab_config.get_subcloud(subcloud_name)

        subcloud_ip = subcloud_obj.get_floating_ip()
        subcloud_psswr = subcloud_obj.get_admin_credentials().get_password()
        bmc_psswr = subcloud_obj.get_bm_password()
        release = "" if release_id is None else f"--release {release_id}"

        cmd = source_openrc(f"dcmanager subcloud add --migrate --bootstrap-address {subcloud_ip} " f"--bootstrap-values {bootstrap_values} --install-values {install_values}" f" --sysadmin-password {subcloud_psswr} --bmc-password {bmc_psswr} {release}")

        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

    def dcmanager_subcloud_add_enroll(self, subcloud_name: str, bootstrap_values: str, install_values: str, deploy_config_file: str):
        """Runs 'dcmanager subcloud add --enroll' command.

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
        bmc_psswr = subcloud_obj.get_bm_password() or subcloud_psswr
        cmd = f"dcmanager subcloud add --enroll" f" --bootstrap-address {subcloud_ip}" f" --bootstrap-values {bootstrap_values}" f" --install-values {install_values}" f" --deploy-config {deploy_config_file}" f" --sysadmin-password {subcloud_psswr}" f" --bmc-password {bmc_psswr}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def dcmanager_subcloud_add_enroll_with_error(self, subcloud_name: str, bootstrap_values: str, install_values: str, deploy_config_file: str) -> tuple:
        """Runs 'dcmanager subcloud add --enroll' and returns output and rc without asserting.

        Used for negative testing where the command is expected to be rejected.

        Args:
            subcloud_name (str): Subcloud name.
            bootstrap_values (str): Bootstrap values file name.
            install_values (str): Install values file name.
            deploy_config_file (str): Deployment config file name.

        Returns:
            tuple: (output_str, return_code_int).
        """
        lab_config = ConfigurationManager.get_lab_config()
        subcloud_obj = lab_config.get_subcloud(subcloud_name)
        subcloud_ip = subcloud_obj.get_floating_ip()
        subcloud_psswr = subcloud_obj.get_admin_credentials().get_password()
        bmc_psswr = subcloud_obj.get_bm_password() or subcloud_psswr
        cmd = f"dcmanager subcloud add --enroll" f" --bootstrap-address {subcloud_ip}" f" --bootstrap-values {bootstrap_values}" f" --install-values {install_values}" f" --deploy-config {deploy_config_file}" f" --sysadmin-password {subcloud_psswr}" f" --bmc-password {bmc_psswr}"
        output = self.ssh_connection.send(source_openrc(cmd))
        rc = self.ssh_connection.get_return_code()
        if isinstance(output, list):
            output = "\n".join(str(line).strip() for line in output)
        return output, rc

from config.configuration_manager import ConfigurationManager
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_show_output import DcManagerSubcloudDeployShowOutput


class DCManagerSubcloudDeployKeywords(BaseKeyword):
    """
    This class defines the keywords for subcloud phased subcloud deployment operations.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor

        Args:
            ssh_connection (SSHConnection): ssh for the active controller
        """
        self.ssh_connection = ssh_connection

    def dcmanager_subcloud_deploy_abort(self, subcloud_name: str):
        """Aborts the subcloud deployment using 'dcmanager subcloud deploy abort'.

        Args:
            subcloud_name (str): a str name for the subcloud.
        """
        # Execute the command
        cmd = f"dcmanager subcloud deploy abort {subcloud_name}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def dcmanager_subcloud_deploy_complete(self, subcloud_name: str):
        """Completes the subcloud deployment using 'dcmanager subcloud deploy complete'.

        Args:
            subcloud_name (str): a str name for the subcloud.
        """
        # Execute the command
        cmd = f"dcmanager subcloud deploy complete {subcloud_name}"
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

    def dcmanager_subcloud_deploy_create(self, subcloud_name: str, wait_for_status: bool = True):
        """Creates the subcloud using 'dcmanager subcloud deploy create'.

        Args:
            subcloud_name (str): a str name for the subcloud.
            wait_for_status (bool): wheteher to check for status or not default is True
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
        # Execute the command
        cmd = f"dcmanager subcloud deploy create --bootstrap-address {boot_add} --bootstrap-values {bootstrap_file} --install-values {install_file} --bmc-password {sc_config.get_bm_password()} --deploy-config {deploy_file} "
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        if wait_for_status:
            success_status = "create-complete"
            dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, success_status)

    def dcmanager_subcloud_deploy_install(self, subcloud_name: str, wait_for_status: bool = True):
        """Installs the subcloud using 'dcmanager subcloud deploy install'.

        Args:
            subcloud_name (str): a str name for the subcloud.
            wait_for_status (bool): wheteher to check for status or not default is True
        """
        # Get the subcloud config
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)

        admin_creds = sc_config.get_admin_credentials()
        install_file = sc_assets.get_install_file()

        # Execute the command
        cmd = f"dcmanager subcloud deploy install {subcloud_name} --sysadmin-password {admin_creds.get_password()} --bmc-password {sc_config.get_bm_password()} --install-values {install_file} "
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        if wait_for_status:
            success_status = "install-complete"
            dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, success_status)

    def dcmanager_subcloud_deploy_bootstrap(self, subcloud_name: str, wait_for_status: bool = True):
        """Bootstraps the subcloud using 'dcmanager subcloud deploy bootstrap'.

        Args:
            subcloud_name (str): a str name for the subcloud.
            wait_for_status (bool): wheteher to check for status or not default is True
        """
        # Get the subcloud config
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)

        admin_creds = sc_config.get_admin_credentials()
        bootstrap_file = sc_assets.get_bootstrap_file()
        # Get the subcloud bootstrap address
        boot_add = sc_config.get_first_controller().get_ip()

        # Execute the command
        cmd = f"dcmanager subcloud deploy bootstrap {subcloud_name} --sysadmin-password {admin_creds.get_password()} --bootstrap-address {boot_add} --bootstrap-values {bootstrap_file} "
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        if wait_for_status:
            success_status = "bootstrap-complete"
            dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, success_status)

    def dcmanager_subcloud_deploy_config(self, subcloud_name: str, wait_for_status: bool = True):
        """Configures the subcloud using 'dcmanager subcloud deploy config'.

        Args:
            subcloud_name (str): a str name for the subcloud.
            wait_for_status (bool): wheteher to check for status or not default is True
        """
        # Get the subcloud config
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)

        admin_creds = sc_config.get_admin_credentials()
        deploy_file = sc_assets.get_deployment_config_file()

        # Execute the command
        cmd = f"dcmanager subcloud deploy config {subcloud_name} --sysadmin-password {admin_creds.get_password()} --deploy-config {deploy_file} "
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        if wait_for_status:
            success_status = "complete"
            dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, success_status)

    def dcmanager_subcloud_deploy_resume(self, subcloud_name: str, wait_for_status: bool = True):
        """Creates the subcloud using 'dcmanager subcloud deploy resume'.

        Args:
            subcloud_name (str): a str name for the subcloud.
            wait_for_status (bool): wheteher to check for status or not default is True
        """
        # Get the subcloud config
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        # Get the subcloud deployment assets
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)
        bootstrap_file = sc_assets.get_bootstrap_file()
        deploy_file = sc_assets.get_deployment_config_file()
        admin_creds = sc_config.get_admin_credentials()

        # Get the subcloud bootstrap address
        boot_add = sc_config.get_first_controller().get_ip()
        # Execute the command
        cmd = f"dcmanager subcloud deploy resume {subcloud_name} --bootstrap-address {boot_add} --bootstrap-values {bootstrap_file} --deploy-config {deploy_file} --sysadmin-password {admin_creds.get_password()} --bmc-password {sc_config.get_bm_password()} "
        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        # validate subcloud status until complete
        if wait_for_status:
            success_status = "complete"
            dc_manager_sc_list_kw = DcManagerSubcloudListKeywords(self.ssh_connection)
            dc_manager_sc_list_kw.validate_subcloud_status(subcloud_name, success_status)

    def dcmanager_subcloud_deploy_upload(self, update_deploy_params: bool = False, prestaging_images: bool = False, release_version: str = None) -> DcManagerSubcloudDeployShowOutput:
        """Uploads deployment files using dcmanager subcloud deploy upload command.

        Args:
            update_deploy_params (bool): Whether to update deploy parameters.
            prestaging_images (bool): Whether to include prestaging images file.
            release_version (str): The release version to use.

        Returns:
            DcManagerSubcloudDeployShowOutput: The output object containing the deployment upload details.

        Raises:
            Exception: If none of the parameters are provided.
        """
        if not update_deploy_params and not prestaging_images:
            raise Exception("At least one parameter must be provided: update_deploy_params, prestaging_images")

        cmd_parts = ["dcmanager subcloud deploy upload"]
        controller_deployment_assets = ConfigurationManager.get_deployment_assets_config().get_controller_deployment_assets()

        if update_deploy_params:
            cmd_parts.extend(["--deploy-playbook", controller_deployment_assets.get_deploy_playbook_file(), "--deploy-overrides", controller_deployment_assets.get_deploy_overrides_file(), "--deploy-chart", controller_deployment_assets.get_deploy_chart_file()])

        if prestaging_images:
            cmd_parts.extend(["--prestage-images", controller_deployment_assets.get_prestage_images_file()])

        if release_version:
            cmd_parts.extend(["--release", release_version])

        cmd = " ".join(cmd_parts)
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return DcManagerSubcloudDeployShowOutput(output)

    def dcmanager_subcloud_deploy_upload_with_error(self, update_deploy_params: bool = False, prestaging_images: bool = False, release_version: str = None) -> str:
        """
        Upload deployment files using dcmanager subcloud deploy upload command (error handling version).

        Args:
            update_deploy_params (bool): Whether to update deploy parameters.
            prestaging_images (bool): Whether to include prestaging images file.
            release_version (str): The release version to use.

        Returns:
            str: Raw command output (for error validation).
        """
        cmd_parts = ["dcmanager subcloud deploy upload"]
        controller_deployment_assets = ConfigurationManager.get_deployment_assets_config().get_controller_deployment_assets()

        if update_deploy_params:
            cmd_parts.extend(["--deploy-playbook", controller_deployment_assets.get_deploy_playbook_file(), "--deploy-overrides", controller_deployment_assets.get_deploy_overrides_file(), "--deploy-chart", controller_deployment_assets.get_deploy_chart_file()])

        if prestaging_images:
            cmd_parts.extend(["--prestage-images", controller_deployment_assets.get_prestage_images_file()])

        if release_version:
            cmd_parts.extend(["--release", release_version])

        cmd = " ".join(cmd_parts)
        output = self.ssh_connection.send(source_openrc(cmd))
        if isinstance(output, list) and len(output) > 0:
            return "\n".join(line.strip() for line in output)
        return output.strip() if isinstance(output, str) else str(output)

    def dcmanager_subcloud_redeploy(self, subcloud_name: str, install_values: str, wait_for_status: bool):
        """
        Redeploy the subcloud using 'dcmanager subcloud redeploy' command.

        Args:
            subcloud_name (str): subcloud name.
            install_values (str): install-values.yml file path. Default to use install values file from deployment assets.
            wait_for_status (bool): If true waits for a 'complete' status.
        """

        # Get the subcloud config
        deployment_assets_config = ConfigurationManager.get_deployment_assets_config()
        sc_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        sc_assets = deployment_assets_config.get_subcloud_deployment_assets(subcloud_name)

        if not install_values:
            install_values = sc_assets.get_install_file()

        admin_creds = sc_config.get_admin_credentials()

        cmd = f"dcmanager subcloud redeploy {subcloud_name} --install-values {install_values} --sysadmin-password {admin_creds} --bmc-password {admin_creds}"
        print(cmd)

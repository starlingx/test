import os
import re

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_list_keywords import DcManagerSubcloudListKeywords
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_config_files_object import DcManagerSubcloudConfigFilesObject
from keywords.cloud_platform.dcmanager.objects.dcmanager_subcloud_deploy_object import DcManagerSubcloudDeployObject


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

    # States of the subcloud create
    CREATE_EXECUTION_FAILED = "create-failed"
    CREATE_EXECUTED = "create-complete"

    # States of the subcloud install
    INSTALL_EXECUTION_FAILED = "install-failed"
    INSTALL_EXECUTING = "installing"
    INSTALL_EXECUTED = "install-complete"

    # States of the subcloud bootstrap
    BOOTSTRAP_EXECUTION_FAILED = "bootstrap-failed"
    BOOTSTRAP_EXECUTING = "bootstrapping"
    BOOTSTRAP_EXECUTED = "bootstrap-complete"

    # States of the subcloud config
    CONFIG_EXECUTION_FAILED = "config-failed"
    CONFIG_EXECUTED = "complete"

    # Timeout values for the states of subcloud deploy
    SUBCLOUD_DEPLOY_CREATE = 180
    SUBCLOUD_DEPLOY_INSTALL = 1200
    SUBCLOUD_DEPLOY_BOOTSTRAP = 2700
    SUBCLOUD_DEPLOY_CONFIG = 2700

    def find_config_filename(self, folder_path: str, phase: str, files: list[str]) -> str:
        """
        Find the configuration filename for a specific phase in the given folder.

        Args:
            folder_path (str): The path to the folder containing configuration files
            phase (str): The deployment phase to find (e.g., 'install', 'bootstrap', 'deploy')
            files (list[str]): List of filenames in the folder to search through

        Returns:
            str: The full path to the configuration file for the specified phase

        Raises:
            ValueError: If files list is empty or None
            FileNotFoundError: If no configuration file is found for the specified phase
        """
        if not files:
            error_msg = f"No files found in folder {folder_path} for phase {phase}"
            get_logger().log_error(error_msg)
            raise ValueError(error_msg)

        matching_files = [file_name for file_name in files if phase in file_name]
        if not matching_files:
            error_msg = f"No configuration file found for phase {phase} in {folder_path}"
            get_logger().log_error(error_msg)
            raise FileNotFoundError(error_msg)

        # Use the first matching file if multiple exist
        config_file = os.path.join(folder_path, matching_files[0].rstrip("\n"))
        get_logger().log_info(f"Found configuration file for phase {phase}: {config_file}")
        return config_file

    def get_subcloud_config_files(self, subcloud: str) -> DcManagerSubcloudConfigFilesObject:
        """
        Get subcloud config YAML files

        Args:
            subcloud (str): Name of the subcloud

        Returns:
            DcManagerSubcloudConfigFilesObject: Object containing paths to configuration files
        """
        lab_config = ConfigurationManager.get_lab_config()
        user_name = lab_config.get_admin_credentials().get_user_name()
        match = re.search(r"\d+$", subcloud)
        num = int(match.group())
        folder_name = f"subcloud-{num}"

        subcloud_folder = f"/home/{user_name}/{folder_name}"
        get_logger().log_info(f"subcloud_folder  {subcloud_folder}")

        file_phases = ["install", "bootstrap", "deploy"]
        files = self.ssh_connection.send(f"ls {subcloud_folder}")

        install_file = None
        bootstrap_file = None
        deploy_file = None

        for phase in file_phases:
            file_name = self.find_config_filename(subcloud_folder, phase, files)
            get_logger().log_info(f"config file of {phase} is {file_name}")

            if phase == "install":
                install_file = file_name
            elif phase == "bootstrap":
                bootstrap_file = file_name
            elif phase == "deploy":
                deploy_file = file_name

        return DcManagerSubcloudConfigFilesObject(install_file=install_file, bootstrap_file=bootstrap_file, deploy_file=deploy_file)

    def check_deploy_status(self, subcloud: str) -> str:
        """
        Get the deploy status of the subcloud

        Args:
            subcloud (str): Name or ID of the subcloud

        Returns:
            str:
                Deployment status of the subcloud(deploy_status)

        """
        dcmanager_subcloud_list_keywords = DcManagerSubcloudListKeywords(self.ssh_connection)
        dcmanager_subcloud_list = dcmanager_subcloud_list_keywords.get_dcmanager_subcloud_list()
        subcloud = dcmanager_subcloud_list.get_subcloud_by_name(subcloud)
        deploy_status = subcloud.get_deploy_status()
        return deploy_status

    def deploy_create_subcloud(
        self,
        deploy_params: DcManagerSubcloudDeployObject,
    ) -> str:
        """
        Perform subcloud configuration on the System Controller without execution of subsequent phases

        Args:
            deploy_params (DcManagerSubcloudDeployObject): Object containing all deployment parameters

        Returns:
                str:
                    Deployment status of the subcloud(deploy_status)
        """
        operation = "create"
        subcloud = deploy_params.get_subcloud()
        get_logger().log_info(f"Attempt to deploy {operation} : {subcloud}")

        cmd = f"dcmanager subcloud deploy {operation} --bootstrap-address {deploy_params.get_bootstrap_address()} --bootstrap-values {deploy_params.get_bootstrap_values()}"

        if deploy_params.get_install_values():
            cmd += f" --install-values {deploy_params.get_install_values()}"
        if deploy_params.get_bmc_password():
            cmd += f" --bmc-password {deploy_params.get_bmc_password()}"
        if deploy_params.get_deploy_config():
            cmd += f" --deploy-config {deploy_params.get_deploy_config()}"
        if deploy_params.get_group():
            cmd += f" --group {deploy_params.get_group()}"
        if deploy_params.get_release():
            cmd += f" --release {deploy_params.get_release()}"

        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        def check_deploy_create_status() -> str:
            """
            Checks the subcloud deploy status
            """
            return self.check_deploy_status(subcloud)

        check_interval = 30
        validate_equals_with_retry(
            function_to_execute=check_deploy_create_status,
            expected_value=self.CREATE_EXECUTED,
            validation_description=f"Deploy create for subcloud {subcloud} completed.",
            timeout=self.SUBCLOUD_DEPLOY_CREATE,
            polling_sleep_time=check_interval,
        )

        subcloud_obj = DcManagerSubcloudListKeywords(self.ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud)
        deploy_status = subcloud_obj.get_deploy_status()
        return deploy_status

    def deploy_install_subcloud(
        self,
        deploy_params: DcManagerSubcloudDeployObject,
    ) -> str:
        """
        Perform install operation only (no bootstrap)

        Args:
            deploy_params (DcManagerSubcloudDeployObject): Object containing all deployment parameters

        Returns:
                str:
                    Deployment status of the subcloud(deploy_status)
        """
        operation = "install"
        subcloud = deploy_params.get_subcloud()
        get_logger().log_info(f"Attempt to deploy {operation} : {subcloud}")

        # Get sysadmin password from lab config
        sysadmin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        cmd = f"dcmanager subcloud deploy {operation} {subcloud} --sysadmin-password {sysadmin_password}"

        if deploy_params.get_install_values():
            cmd += f" --install-values {deploy_params.get_install_values()}"
        if deploy_params.get_bmc_password():
            cmd += f" --bmc-password {deploy_params.get_bmc_password()}"
        if deploy_params.get_group():
            cmd += f" --group {deploy_params.get_group()}"
        if deploy_params.get_release():
            cmd += f" --release {deploy_params.get_release()}"

        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        def check_deploy_install_status() -> str:
            """
            Checks the subcloud deploy status
            """
            return self.check_deploy_status(subcloud)

        check_interval = 60
        validate_equals_with_retry(
            function_to_execute=check_deploy_install_status,
            expected_value=self.INSTALL_EXECUTED,
            validation_description=f"Deploy install for subcloud {subcloud} completed.",
            timeout=self.SUBCLOUD_DEPLOY_INSTALL,
            polling_sleep_time=check_interval,
        )

        subcloud_obj = DcManagerSubcloudListKeywords(self.ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud)
        deploy_status = subcloud_obj.get_deploy_status()
        return deploy_status

    def deploy_bootstrap_subcloud(
        self,
        deploy_params: DcManagerSubcloudDeployObject,
    ) -> str:
        """
        Perform the bootstrap operation only (perform play or replay)

        Args:
            deploy_params (DcManagerSubcloudDeployObject): Object containing all deployment parameters

        Returns:
                str:
                    Deployment status of the subcloud(deploy_status)
        """
        operation = "bootstrap"
        subcloud = deploy_params.get_subcloud()
        get_logger().log_info(f"Attempt to deploy {operation} : {subcloud}")

        # Get sysadmin password from lab config
        sysadmin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        cmd = f"dcmanager subcloud deploy {operation} {subcloud} --sysadmin-password {sysadmin_password}"

        if deploy_params.get_bootstrap_values():
            cmd += f" --bootstrap-values {deploy_params.get_bootstrap_values()}"
        if deploy_params.get_bootstrap_address():
            cmd += f" --bootstrap-address {deploy_params.get_bootstrap_address()}"

        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        def check_deploy_bootstrap_status() -> str:
            """
            Checks the subcloud deploy status
            """
            return self.check_deploy_status(subcloud)

        check_interval = 60
        validate_equals_with_retry(
            function_to_execute=check_deploy_bootstrap_status,
            expected_value=self.BOOTSTRAP_EXECUTED,
            validation_description=f"Deploy bootstrap for subcloud {subcloud} completed.",
            timeout=self.SUBCLOUD_DEPLOY_BOOTSTRAP,
            polling_sleep_time=check_interval,
        )

        subcloud_obj = DcManagerSubcloudListKeywords(self.ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud)
        deploy_status = subcloud_obj.get_deploy_status()
        return deploy_status

    def deploy_config_subcloud(
        self,
        deploy_params: DcManagerSubcloudDeployObject,
    ) -> str:
        """
        Perform deployment config/reconfig only

        Args:
            deploy_params (DcManagerSubcloudDeployObject): Object containing all deployment parameters

        Returns:
                str:
                    Deployment status of the subcloud(deploy_status)
        """
        operation = "config"
        subcloud = deploy_params.get_subcloud()
        get_logger().log_info(f"Attempt to deploy {operation} : {subcloud}")

        # Get sysadmin password from lab config
        sysadmin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        cmd = f"dcmanager subcloud deploy {operation} {subcloud} --sysadmin-password {sysadmin_password}"

        if deploy_params.get_deploy_config():
            cmd += f" --deploy-config {deploy_params.get_deploy_config()}"

        self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)

        def check_deploy_config_status() -> str:
            """
            Checks the subcloud deploy status
            """
            return self.check_deploy_status(subcloud)

        check_interval = 60
        validate_equals_with_retry(
            function_to_execute=check_deploy_config_status,
            expected_value=self.CONFIG_EXECUTED,
            validation_description=f"Deploy config for subcloud {subcloud} completed.",
            timeout=self.SUBCLOUD_DEPLOY_CONFIG,
            polling_sleep_time=check_interval,
        )

        subcloud_obj = DcManagerSubcloudListKeywords(self.ssh_connection).get_dcmanager_subcloud_list().get_subcloud_by_name(subcloud)
        deploy_status = subcloud_obj.get_deploy_status()
        return deploy_status

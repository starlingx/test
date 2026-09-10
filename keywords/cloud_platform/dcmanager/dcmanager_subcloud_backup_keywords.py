from typing import List, Optional

from config.configuration_manager import ConfigurationManager
from config.lab.objects.lab_type_enum import LabTypeEnum
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import oidc_auth_wrap, source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_state_watcher_keywords import BACKUP_IN_PROGRESS_STATES, RESTORE_IN_PROGRESS_STATES, DcManagerSubcloudStateWatcherKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.server.power_keywords import PowerKeywords

CENTRAL_BACKUP_PATH = "/opt/dc-vault/backups/"
LOCAL_BACKUP_PATH = "/opt/platform-backup/backups/"
COMPLETE_CENTRAL_STATUS = "complete-central"
COMPLETE_LOCAL_STATUS = "complete-local"
RESTORE_COMPLETE_STATUS = "complete"


class DcManagerSubcloudBackupKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud-backup <create/delete>' command.
    """

    def __init__(self, ssh_connection: SSHConnection, use_oidc: bool = False):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
            use_oidc (bool): If True, use OIDC authentication instead of source_openrc.
        """
        self.ssh_connection = ssh_connection
        self.use_oidc = use_oidc

    def _wrap_command(self, cmd: str) -> str:
        """Wrap a dcmanager command with the appropriate auth method.

        Args:
            cmd (str): Raw dcmanager command.

        Returns:
            str: Command wrapped with either source_openrc or OIDC auth.
        """
        if self.use_oidc:
            return oidc_auth_wrap(cmd)
        return source_openrc(cmd)

    def get_backup_path(self, subcloud_name: str, release: str, local_only: bool = False) -> str:
        """
        Generate the backup path for a given subcloud and release.

        Args:
            subcloud_name (str): The name of the subcloud.
            release (str): The release version associated with the backup.
            local_only (bool, optional): If True, returns the local subcloud backup path;
                                        otherwise, returns the central cloud backup path. Defaults to False.

        Returns:
            str: The full backup path based on the given parameters.
        """
        if local_only:
            return f"/opt/platform-backup/backups/{release}/"

        return f"/opt/dc-vault/backups/{subcloud_name}/{release}/"

    # fmt: off
    def create_subcloud_backup_expect_fail(
        self,
        sysadmin_password: str,
        con_ssh: SSHConnection,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        backup_yaml: Optional[str] = None,
        group: Optional[str] = None,
        registry: bool = False,
        subcloud_list: Optional[list] = None,
        expect_cmd_rejection: Optional[bool] = False,
    ) -> None:
        # fmt: on
        """
        Runs backup creation command expecting it to fail.

        Args:
            sysadmin_password (str): Subcloud sysadmin password needed for backup creation.
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            subcloud (Optional[str]): The name of the subcloud to backup. Defaults to None.
            local_only (bool): If True, backup will be stored only in the subcloud. Defaults to False.
            backup_yaml (Optional[str]): path to use the yaml file. Defaults to None.
            group (Optional[str]): Subcloud group name to create backup. Defaults to None.
            registry (bool): Option to add the registry backup in the same task. Defaults to False.
            subcloud_list (Optional[list]): List of subcloud names when backing up a group. Defaults to None.
            expect_cmd_rejection (Optional[bool]): Expect backup command to be rejected if True. Default to False

        Returns:
            None:
        """
        # Command construction
        cmd = f"dcmanager subcloud-backup create --sysadmin-password {sysadmin_password}"
        if subcloud:
            cmd += f" --subcloud {subcloud}"
        if local_only:
            cmd += " --local-only"
        if backup_yaml:
            cmd += f" --backup-values {backup_yaml}"
        if group:
            cmd += f" --group {group}"
        if registry:
            cmd += " --registry-images"

        self.ssh_connection.send(self._wrap_command(cmd))
        if expect_cmd_rejection:
            rejected = self.validate_cmd_rejection_return_code(self.ssh_connection)
            validate_equals(rejected, True, "Validate backup command was rejected.")

        else:
            self.validate_success_return_code(self.ssh_connection)
            if group:
                for subcloud_name in subcloud_list:
                    ssh_connection = LabConnectionKeywords().get_subcloud_ssh(subcloud_name) if local_only else con_ssh

                    self.wait_for_backup_failure(ssh_connection, subcloud_name)

            else:
                self.wait_for_backup_failure(con_ssh, subcloud)

    def wait_for_backup_failure(
        self,
        con_ssh: SSHConnection,
        subcloud: Optional[str],
        check_interval: int = 30,
        timeout: int = 300,
    ) -> None:
        """
        Waits for backup operation to fail

        Args:
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            subcloud (Optional[str]): The name of the subcloud to check.
            check_interval (int): Time interval (in seconds) to check for file creation. Defaults to 30.
            timeout (int): Maximum time (in seconds) to wait for file creation. Defaults to 120.

        Returns:
            None:
        """

        def check_for_failure() -> bool:
            """
            Checks if the backup creation has failed.

            Returns:
                bool: True if operation failed, False if didn't.
            """
            bckp_status = DcManagerSubcloudShowKeywords(con_ssh).get_dcmanager_subcloud_show(subcloud_name=subcloud).get_dcmanager_subcloud_show_object().get_backup_status()
            if bckp_status == "failed":
                return True
            else:
                return False

        validate_equals_with_retry(function_to_execute=check_for_failure, expected_value=True, validation_description="Backup creation failed.", timeout=timeout, polling_sleep_time=check_interval)

    # fmt: off
    def create_subcloud_backup(
        self,
        sysadmin_password: str,
        con_ssh: SSHConnection,
        path: Optional[str] = None,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        backup_yaml: Optional[str] = None,
        group: Optional[str] = None,
        registry: bool = False,
        release: Optional[str] = None,
        subcloud_list: Optional[list] = None,
        wait: bool = True,
    ) -> None:
        # fmt: on
        """
        Creates a backup of the specified subcloud.

        Args:
            sysadmin_password (str): Subcloud sysadmin password needed for backup creation.
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            path (Optional[str]): The directory path where the backup file will be checked.
            subcloud (Optional[str]): The name of the subcloud to backup. Defaults to None.
            local_only (bool): If True, backup will be stored only in the subcloud. Defaults to False.
            backup_yaml (Optional[str]): path to use the yaml file. Defaults to None.
            group (Optional[str]): Subcloud group name to create backup. Defaults to None.
            registry (bool): Option to add the registry backup in the same task. Defaults to False.
            release (Optional[str]): Release version required to check backup. Defaults to None.
            subcloud_list (Optional[list]): List of subcloud names when backing up a group. Defaults to None.
            wait (bool): If True, wait for backup completion internally. Set False to trigger only and
                let the caller own the completion wait. Defaults to True.

        Returns:
            None:
        """
        # Command construction
        cmd = f"dcmanager subcloud-backup create --sysadmin-password {sysadmin_password}"
        if subcloud:
            cmd += f" --subcloud {subcloud}"
        if local_only:
            cmd += " --local-only"
        if backup_yaml:
            cmd += f" --backup-values {backup_yaml}"
        if group:
            cmd += f" --group {group}"
        if registry:
            cmd += " --registry-images"

        self.ssh_connection.send(self._wrap_command(cmd))
        self.validate_success_return_code(self.ssh_connection)

        if not wait:
            return

        if group:
            for subcloud_name in subcloud_list:
                ssh_connection = LabConnectionKeywords().get_subcloud_ssh(subcloud_name) if local_only else con_ssh
                backup_path = self.get_backup_path(subcloud_name, release, local_only)

                if local_only:
                    backup_path = f"{backup_path}{subcloud_name}_platform_backup_*.tgz"

                self.wait_for_backup_creation(ssh_connection, backup_path, subcloud_name)

        else:
            # Wait for backup to initiate to avoid false validation.
            self.wait_for_backup_status_complete(subcloud=subcloud, expected_status="backing-up", check_interval=2, timeout=30)

            if path:
                ssh_connection = LabConnectionKeywords().get_subcloud_ssh(subcloud) if local_only else con_ssh
                self.wait_for_backup_creation(ssh_connection, path, subcloud)

    def wait_for_backup_creation(
        self,
        con_ssh: SSHConnection,
        path: str,
        subcloud: Optional[str],
        check_interval: int = 30,
        timeout: int = 600,
    ) -> None:
        """
        Waits for the backup file to be created in the specified path.

        Args:
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            path (str): The path where the backup file is expected.
            subcloud (Optional[str]): The name of the subcloud to check.
            check_interval (int): Time interval (in seconds) to check for file creation. Defaults to 30.
            timeout (int): Maximum time (in seconds) to wait for file creation. Defaults to 600.

        Returns:
            None:
        """

        def check_backup_created() -> str:
            """
            Checks if the backup has been created.

            Returns:
                str: A message indicating whether the backup has been successfully created or not.
            """
            check_file = FileKeywords(con_ssh).validate_file_exists_with_sudo(path)
            if check_file:
                return f"Backup should be created at {path}"
            else:
                return "Backup not created yet."

        validate_equals_with_retry(
            function_to_execute=check_backup_created,
            expected_value=f"Backup should be created at {path}",
            validation_description=f"Backup creation for subcloud {subcloud} completed.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

    def reject_delete_subcloud_backup(
        self,
        con_ssh: SSHConnection,
        release: str,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        group: Optional[str] = None,
        sysadmin_password: Optional[str] = None,
    ) -> None:
        """
        Sends the command to delete the backup of the specified subcloud and expects a command rejection.

        Args:
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            release (str): Required to delete a release backup.
            subcloud (Optional[str]): The name of the subcloud to delete the backup. Defaults to None.
            local_only (bool): If True, only deletes the local backup in the subcloud. Defaults to False.
            group (Optional[str]): Subcloud group name to delete backup. Defaults to None.
            sysadmin_password (str): Subcloud sysadmin password needed for deletion on local_path. Defaults to None.

        Returns:
            None:
        """
        # Command construction for backup deletion
        cmd = f"dcmanager subcloud-backup delete {release}"
        if subcloud:
            cmd += f" --subcloud {subcloud}"
        if local_only:
            cmd += " --local-only"
        if group:
            cmd += f" --group {group}"
        if sysadmin_password:
            cmd += f" --sysadmin-password {sysadmin_password}"

        self.ssh_connection.send(self._wrap_command(cmd))
        rejected = self.validate_cmd_rejection_return_code(self.ssh_connection)
        validate_equals(rejected, True, "Validate backup command was rejected.")

    def delete_subcloud_backup(
        self,
        con_ssh: SSHConnection,
        release: str,
        path: Optional[str] = None,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        group: Optional[str] = None,
        sysadmin_password: Optional[str] = None,
        subcloud_list: Optional[list] = None,
    ) -> None:
        """
        Sends the command to delete the backup of the specified subcloud and waits for confirmation of its deletion.

        Args:
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            release (str): Required to delete a release backup.
            path (Optional[str]): The path where the backup file is located. Defaults to None.
            subcloud (Optional[str]): The name of the subcloud to delete the backup. Defaults to None.
            local_only (bool): If True, only deletes the local backup in the subcloud. Defaults to False.
            group (Optional[str]): Subcloud group name to delete backup. Defaults to None.
            sysadmin_password (str): Subcloud sysadmin password needed for deletion on local_path. Defaults to None.
            subcloud_list (Optional[list]): List of subcloud names when deleting backups for a group. Defaults to None.

        Returns:
            None:
        """
        # Command construction for backup deletion
        cmd = f"dcmanager subcloud-backup delete {release}"
        if subcloud:
            cmd += f" --subcloud {subcloud}"
        if local_only:
            cmd += " --local-only"
        if group:
            cmd += f" --group {group}"
        if sysadmin_password:
            cmd += f" --sysadmin-password {sysadmin_password}"

        self.ssh_connection.send(self._wrap_command(cmd))
        self.validate_success_return_code(self.ssh_connection)

        if group:
            for subcloud_name in subcloud_list:
                ssh_connection = LabConnectionKeywords().get_subcloud_ssh(subcloud_name) if local_only else con_ssh
                backup_path = self.get_backup_path(subcloud_name, release, local_only)

                self.wait_for_backup_deletion(ssh_connection, backup_path, subcloud_name)
        else:
            self.wait_for_backup_deletion(con_ssh, path, subcloud)

    def wait_for_backup_deletion(self, con_ssh: SSHConnection, path: str, subcloud: str) -> None:
        """
        Waits for the backup to be deleted by checking for the absence of the backup file.

        Args:
            con_ssh (SSHConnection): SSH connection object to execute the command.
            path (str): The path where the backup file was located.
            subcloud (str): The name of the subcloud to delete the backup.

        Returns:
            None:
        """

        def check_backup_deleted() -> str:
            """
            Checks if the backup has been deleted.

            Returns:
                str: Confirmation message if the backup is deleted, otherwise an error message.
            """
            check_file = FileKeywords(con_ssh).validate_file_exists_with_sudo(path)
            if not check_file:
                return f"Backup successfully deleted from {path} for {subcloud}"
            else:
                return f"Backup still exists at {path}."

        # Using validate_equals_with_retry to ensure the backup is deleted.
        validate_equals_with_retry(function_to_execute=check_backup_deleted, expected_value=f"Backup successfully deleted from {path} for {subcloud}", validation_description=f"Backup deletion for subcloud {subcloud} completed.", timeout=60)

    def wait_for_backup_status_complete(
        self,
        subcloud: str,
        expected_status: str,
        check_interval: int = 30,
        timeout: int = 600,
    ) -> None:
        """
        Waits for subcloud backup status to be the expected status.

        Args:
            subcloud (str): The name of the subcloud to check.
            expected_status (str): Sets status to be verified.
            check_interval (int): Time interval (in seconds) to check for file creation. Defaults to 30.
            timeout (int): Maximum time (in seconds) to wait for file creation. Defaults to 600.

        Returns:
            None:
        """

        def check_backup_status_completed() -> bool:
            """
            Checks if the backup has been created.

            Returns:
                bool: Return if backup condition is met.
            """
            dcmanager_subcloud_obj = DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud).get_dcmanager_subcloud_show_object()
            backup_flag = dcmanager_subcloud_obj.get_backup_status()
            return backup_flag == expected_status

        validate_equals_with_retry(
            function_to_execute=check_backup_status_completed,
            expected_value=True,
            validation_description=f"Wait for backup creation of subcloud {subcloud} to be {expected_status}.",
            timeout=timeout,
            polling_sleep_time=check_interval,
        )

    def restore_subcloud_backup(
        self,
        sysadmin_password: str,
        con_ssh: SSHConnection,
        with_install: Optional[bool] = False,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        restore_values_path: Optional[str] = None,
        group: Optional[str] = None,
        registry: bool = False,
        factory: bool = False,
        auto_restore: bool = False,
        release: Optional[str] = None,
        subcloud_list: Optional[list] = None,
        timeout: int = 3600,
        wait: bool = True,
    ) -> None:
        """
        Sends the command to restore a subcloud backup.

        Args:
            sysadmin_password (str): Subcloud sysadmin password needed for backup creation.
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            with_install (Optional[bool]): If included, the subcloud will be reinstalled prior to being restored from backup data.
            subcloud (Optional[str]): The name of the subcloud to backup. Defaults to None.
            local_only (bool): If True, backup will be retrieved from file stored in the subcloud. Defaults to False.
            restore_values_path (Optional[str]): Reference to the restore playbook overrides yaml file,
             as listed in the product documentation for the ansible restore. Default as None
            group (Optional[str]): Subcloud group name to create backup. Defaults to None.
            registry (bool): Option to add the registry backup in the same task. Defaults to False.
            factory (bool): Restore from factory backup. Defaults to False.
            auto_restore (bool): Auto-restore mode. Defaults to False.
            release (Optional[str]): Release version required to check backup. Defaults to None.
            subcloud_list (Optional[list]): List of subcloud names when restoring a group backup. Defaults to None.
            timeout (int): Maximum time (in seconds) to wait for the restore to complete. Defaults to 3600.
            wait (bool): If True, wait for restore completion internally. Set False to trigger only and
                let the caller own the completion wait. Defaults to True.
        """
        # Command construction
        cmd = f"dcmanager subcloud-backup restore --sysadmin-password {sysadmin_password}"
        # factory only receives the subcloud parameter, invalidate any other
        if factory:
            get_logger().log_info("Factory install ony receives the subcloud as parameter, invalidating any other.")
            cmd += " --factory"
            local_only = False
            with_install = False
            registry = False
            release = False

        if local_only:
            cmd += " --local-only"
        if subcloud:
            cmd += f" --subcloud {subcloud}"
        if with_install:
            cmd += " --with-install"
        if restore_values_path:
            cmd += f" --restore-values {restore_values_path}"
        if group:
            cmd += f" --group {group}"
        if registry:
            cmd += " --registry-images"
        if release:
            cmd += f" --release {release}"
        if auto_restore:
            cmd += " --auto"

        self.ssh_connection.send(self._wrap_command(cmd))
        self.validate_success_return_code(self.ssh_connection)

        if not wait:
            return

        if group:
            for subcloud_name in subcloud_list:

                self.wait_for_backup_restore(con_ssh, subcloud_name, timeout=timeout)

        else:
            self.wait_for_backup_restore(con_ssh, subcloud, timeout=timeout)

    def wait_for_backup_restore(
        self,
        con_ssh: SSHConnection,
        subcloud: Optional[str],
        check_interval: int = 60,
        timeout: int = 3600,
    ) -> None:
        """
        Waits for the restore operation to be completed.

        Args:
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            subcloud (Optional[str]): The name of the subcloud to check.
            check_interval (int): Time interval (in seconds) to check for file creation. Defaults to 30.
            timeout (int): Maximum time (in seconds) to wait for file creation. Defaults to 600.

        Returns:
            None:
        """

        def check_restore_completed() -> str:
            """
            Checks if restore has been completed.

            Returns:
                str: A message indicating whether the backup has been successfully created or not.
            """
            deploy_status = DcManagerSubcloudShowKeywords(con_ssh).get_dcmanager_subcloud_show(subcloud).get_dcmanager_subcloud_show_object().get_deploy_status()

            if deploy_status == "complete":
                return f"{subcloud} backup restored."
            elif deploy_status == "restore-failed":
                return f"{subcloud} backup restore failed."
            elif deploy_status == "factory-restore-complete":
                return f"{subcloud} backup restored."
            else:
                return "Restore not done yet."

        validate_equals_with_retry(
            function_to_execute=check_restore_completed,
            expected_value=f"{subcloud} backup restored.",
            validation_description=f"Backup restore operation for {subcloud} completed.",
            timeout=timeout,
            polling_sleep_time=check_interval,
            failure_values=[f"{subcloud} backup restore failed."]
        )

    def restore_subcloud_backup_with_error(
        self,
        sysadmin_password: Optional[str] = None,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        group: Optional[str] = None,
        registry: bool = False,
        factory: bool = False,
        auto_restore: bool = False,
        release: Optional[str] = None,
        with_install: bool = False,
    ) -> tuple:
        """Sends the restore command and returns output and rc without asserting.

        Used for negative testing where the command is expected to be rejected.

        Args:
            sysadmin_password (Optional[str]): Subcloud sysadmin password. Defaults to None for testing missing password.
            subcloud (Optional[str]): Name of the subcloud to restore. Defaults to None.
            local_only (bool): If True, restore from local backup. Defaults to False.
            group (Optional[str]): Subcloud group name. Defaults to None.
            registry (bool): Include registry images in restore. Defaults to False.
            factory (bool): Restore from factory backup. Defaults to False.
            auto_restore (bool): Auto-restore mode. Defaults to False.
            release (Optional[str]): Release version. Defaults to None.
            with_install (bool): Reinstall before restore. Defaults to False.

        Returns:
            tuple: (output_str, return_code_int).
        """
        cmd = "dcmanager subcloud-backup restore"
        if sysadmin_password:
            cmd += f" --sysadmin-password {sysadmin_password}"
        if subcloud:
            cmd += f" --subcloud {subcloud}"
        if group:
            cmd += f" --group {group}"
        if local_only:
            cmd += " --local-only"
        if registry:
            cmd += " --registry-images"
        if factory:
            cmd += " --factory"
        if auto_restore:
            cmd += " --auto"
        if release:
            cmd += f" --release {release}"
        if with_install:
            cmd += " --with-install"
        output = self.ssh_connection.send(source_openrc(cmd))
        rc = self.ssh_connection.get_return_code()
        if isinstance(output, list):
            output = "\n".join(str(line).strip() for line in output)
        return output, rc

    def restore_subcloud_backup_prompt_check(self, subcloud: str) -> str:
        """Run restore without --sysadmin-password and capture the password prompt.

        Sends Ctrl+C after detecting the prompt to cancel the operation.
        Used to validate the CLI prompts for password when not provided.

        Args:
            subcloud (str): Name of the subcloud to restore.

        Returns:
            str: The output captured up to and including the password prompt.
        """
        password_prompt = PromptResponse("assword", "\x03")
        shell_prompt = PromptResponse("$", None)
        cmd = source_openrc(f"dcmanager subcloud-backup restore --subcloud {subcloud}")
        self.ssh_connection.send_expect_prompts(cmd, [password_prompt, shell_prompt])
        return password_prompt.get_complete_output()

    # -----------------------------------------------------------------
    # Orchestration helpers (create/restore workflows on top of the CLI)
    # -----------------------------------------------------------------

    def _get_subcloud_password(self, subcloud_name: str) -> str:
        """Return the sysadmin password for a subcloud from lab config.

        Args:
            subcloud_name (str): Subcloud name.

        Returns:
            str: The subcloud sysadmin password.
        """
        return ConfigurationManager.get_lab_config().get_subcloud(subcloud_name).get_admin_credentials().get_password()

    def _get_subcloud_sw_version(self, subcloud_name: str) -> str:
        """Return the software version reported by dcmanager for a subcloud.

        Args:
            subcloud_name (str): Subcloud name.

        Returns:
            str: The subcloud software version.
        """
        return DcManagerSubcloudShowKeywords(self.ssh_connection).get_dcmanager_subcloud_show(subcloud_name).get_dcmanager_subcloud_show_object().get_software_version()

    def _remove_home_backup_archives(self, subcloud_name: str) -> None:
        """Remove leftover platform-backup archives from the subcloud home directory.

        Custom-path local backups are written under /home and are verification
        artifacts only (restore reads from /opt). Left in place they push /home past
        the backup size precheck and cause later backups to fail, so clear any such
        archive before creating a new backup.

        Args:
            subcloud_name (str): Subcloud whose home archives should be cleared.
        """
        lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        home_user = lab_config.get_admin_credentials().get_user_name()
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        home_dir = f"/home/{home_user}/"
        for file_name in FileKeywords(subcloud_ssh).get_files_in_dir(home_dir, is_sudo=True):
            if "platform_backup" in file_name and file_name.endswith(".tgz"):
                FileKeywords(subcloud_ssh).delete_file(f"{home_dir}{file_name}")

    def _create_backup_values_yaml(self, subcloud_name: str, content: str) -> str:
        """Create a backup-values yaml on the system controller.

        Args:
            subcloud_name (str): Subcloud name (used for the file name).
            content (str): YAML content.

        Returns:
            str: The created yaml file name.
        """
        backup_yaml = f"{subcloud_name}_backup_values.yaml"
        FileKeywords(self.ssh_connection).create_file_with_echo(backup_yaml, content)
        return backup_yaml

    def _is_duplex_subcloud(self, subcloud_name: str) -> bool:
        """Return True if the subcloud is configured as a duplex lab.

        Args:
            subcloud_name (str): Subcloud name.

        Returns:
            bool: True if the subcloud lab type is Duplex.
        """
        return ConfigurationManager.get_lab_config().get_subcloud(subcloud_name).get_lab_type() == LabTypeEnum.DUPLEX.value

    def _power_off_if_duplex_install(self, subcloud_name: str, with_install: bool) -> None:
        """Power off all controllers of a duplex subcloud before an install-based restore.

        A duplex restore with install reinstalls the subcloud from scratch, which
        requires the controllers to be powered off first (mirrors DX deployment).
        No-op for simplex subclouds or when the restore does not reinstall.

        Args:
            subcloud_name (str): Subcloud to power off if it is duplex.
            with_install (bool): Whether the restore reinstalls the subcloud.
        """
        if with_install and self._is_duplex_subcloud(subcloud_name):
            get_logger().log_info(f"Powering off duplex subcloud '{subcloud_name}' controllers before install-based restore")
            PowerKeywords(self.ssh_connection).power_off_subcloud(subcloud_name)

    def create_central_backup(self, subcloud_name: str, backup_values: bool = False) -> None:
        """Create a subcloud backup on central storage and wait for completion.

        Args:
            subcloud_name (str): Subcloud to back up.
            backup_values (bool): If True, pass a backup-values yaml with exclude_dirs. Defaults to False.
        """
        password = self._get_subcloud_password(subcloud_name)
        sw_version = self._get_subcloud_sw_version(subcloud_name)
        self._remove_home_backup_archives(subcloud_name)

        backup_yaml = None
        if backup_values:
            backup_yaml = self._create_backup_values_yaml(subcloud_name, 'exclude_dirs: "/opt/patching/**/*"')

        central_path = f"{CENTRAL_BACKUP_PATH}{subcloud_name}/{sw_version}"
        get_logger().log_info(f"Create central backup for subcloud '{subcloud_name}'")
        self.create_subcloud_backup(password, self.ssh_connection, path=central_path, subcloud=subcloud_name, release=sw_version, backup_yaml=backup_yaml, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_single_subcloud(subcloud_name=subcloud_name, field_to_watch="backup_status", in_progress_states=BACKUP_IN_PROGRESS_STATES, complete_state=COMPLETE_CENTRAL_STATUS)

    def create_local_backup(self, subcloud_name: str, custom_path: bool = False, backup_values: bool = False) -> None:
        """Create a subcloud backup on local storage and wait for completion.

        Args:
            subcloud_name (str): Subcloud to back up.
            custom_path (bool): If True, redirect the backup to the home directory. Defaults to False.
            backup_values (bool): If True, pass a backup-values yaml with exclude_dirs. Defaults to False.
        """
        lab_config = ConfigurationManager.get_lab_config().get_subcloud(subcloud_name)
        password = lab_config.get_admin_credentials().get_password()
        sw_version = self._get_subcloud_sw_version(subcloud_name)
        subcloud_ssh = LabConnectionKeywords().get_subcloud_ssh(subcloud_name)
        self._remove_home_backup_archives(subcloud_name)

        backup_yaml = None
        if backup_values:
            backup_yaml = self._create_backup_values_yaml(subcloud_name, 'exclude_dirs: "/opt/patching/**/*"')

        get_logger().log_info(f"Create local backup for subcloud '{subcloud_name}'")

        if custom_path:
            home_user = lab_config.get_admin_credentials().get_user_name()
            home_path = f"/home/{home_user}/"
            backup_yaml = self._create_backup_values_yaml(subcloud_name, f"backup_dir: {home_path}")
            self.create_subcloud_backup(password, subcloud_ssh, path=f"{home_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, backup_yaml=backup_yaml, wait=False)
        else:
            backup_path = f"{LOCAL_BACKUP_PATH}{sw_version}/"
            self.create_subcloud_backup(password, subcloud_ssh, path=f"{backup_path}{subcloud_name}_platform_backup_*.tgz", subcloud=subcloud_name, local_only=True, release=sw_version, backup_yaml=backup_yaml, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_single_subcloud(subcloud_name=subcloud_name, field_to_watch="backup_status", in_progress_states=BACKUP_IN_PROGRESS_STATES, complete_state=COMPLETE_LOCAL_STATUS)

    def create_group_central_backup(self, group_name: str, subcloud_names: List[str]) -> None:
        """Create a central backup for a subcloud group and wait for all to complete.

        Args:
            group_name (str): Name of the group to back up.
            subcloud_names (List[str]): Subclouds in the group.
        """
        password = self._get_subcloud_password(subcloud_names[0])
        release = self._get_subcloud_sw_version(subcloud_names[0])
        get_logger().log_info(f"Create central backup for subcloud group '{group_name}'")
        self.create_subcloud_backup(password, self.ssh_connection, group=group_name, subcloud_list=subcloud_names, release=release, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_subclouds(subcloud_names=subcloud_names, field_to_watch="backup_status", in_progress_states=BACKUP_IN_PROGRESS_STATES, complete_state=COMPLETE_CENTRAL_STATUS)

    def create_group_local_backup(self, group_name: str, subcloud_names: List[str]) -> None:
        """Create a local backup for a subcloud group and wait for all to complete.

        Args:
            group_name (str): Name of the group to back up.
            subcloud_names (List[str]): Subclouds in the group.
        """
        password = self._get_subcloud_password(subcloud_names[0])
        release = self._get_subcloud_sw_version(subcloud_names[0])
        get_logger().log_info(f"Create local backup for subcloud group '{group_name}'")
        self.create_subcloud_backup(password, self.ssh_connection, group=group_name, subcloud_list=subcloud_names, local_only=True, release=release, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_subclouds(subcloud_names=subcloud_names, field_to_watch="backup_status", in_progress_states=BACKUP_IN_PROGRESS_STATES, complete_state=COMPLETE_LOCAL_STATUS)

    def restore_central_backup(self, subcloud_name: str, release: str, override_values: Optional[str] = None, with_install: bool = True) -> None:
        """Restore a subcloud from its central backup of the given release.

        The release identifies which backup to restore; it is independent of the
        subcloud's current running release. Powers off a duplex subcloud's
        controllers before an install-based restore.

        Args:
            subcloud_name (str): Subcloud to restore.
            release (str): Release of the backup to restore (e.g. the N-1 or N-2 backup).
            override_values (Optional[str]): Path to a restore-values yaml. Defaults to None.
            with_install (bool): If True, reinstall before restoring. Defaults to True.
        """
        password = self._get_subcloud_password(subcloud_name)
        self._power_off_if_duplex_install(subcloud_name, with_install)
        get_logger().log_info(f"Restore central backup (release {release}) for subcloud '{subcloud_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, subcloud=subcloud_name, with_install=with_install, release=release, restore_values_path=override_values, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_single_subcloud(subcloud_name=subcloud_name, field_to_watch="deploy_status", in_progress_states=RESTORE_IN_PROGRESS_STATES, complete_state=RESTORE_COMPLETE_STATUS)

    def restore_local_backup(self, subcloud_name: str, release: str, override_values: Optional[str] = None, with_install: bool = True) -> None:
        """Restore a subcloud from its local backup of the given release.

        The release identifies which backup to restore; it is independent of the
        subcloud's current running release. Powers off a duplex subcloud's
        controllers before an install-based restore.

        Args:
            subcloud_name (str): Subcloud to restore.
            release (str): Release of the backup to restore (e.g. the N-1 or N-2 backup).
            override_values (Optional[str]): Path to a restore-values yaml. Defaults to None.
            with_install (bool): If True, reinstall before restoring. Defaults to True.
        """
        password = self._get_subcloud_password(subcloud_name)
        self._power_off_if_duplex_install(subcloud_name, with_install)
        get_logger().log_info(f"Restore local backup (release {release}) for subcloud '{subcloud_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, subcloud=subcloud_name, local_only=True, with_install=with_install, release=release, restore_values_path=override_values, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_single_subcloud(subcloud_name=subcloud_name, field_to_watch="deploy_status", in_progress_states=RESTORE_IN_PROGRESS_STATES, complete_state=RESTORE_COMPLETE_STATUS)

    def auto_restore_central_backup(self, subcloud_name: str, release: str) -> None:
        """Auto-restore a subcloud from its central backup of the given release.

        Args:
            subcloud_name (str): Subcloud to restore.
            release (str): Release of the backup to restore.
        """
        password = self._get_subcloud_password(subcloud_name)
        self._power_off_if_duplex_install(subcloud_name, with_install=True)
        get_logger().log_info(f"Auto-restore central backup (release {release}) for subcloud '{subcloud_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, subcloud=subcloud_name, with_install=True, release=release, auto_restore=True, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_single_subcloud(subcloud_name=subcloud_name, field_to_watch="deploy_status", in_progress_states=RESTORE_IN_PROGRESS_STATES, complete_state=RESTORE_COMPLETE_STATUS)

    def auto_restore_local_backup(self, subcloud_name: str, release: str) -> None:
        """Auto-restore a subcloud from its local backup of the given release.

        Args:
            subcloud_name (str): Subcloud to restore.
            release (str): Release of the backup to restore.
        """
        password = self._get_subcloud_password(subcloud_name)
        self._power_off_if_duplex_install(subcloud_name, with_install=True)
        get_logger().log_info(f"Auto-restore local backup (release {release}) for subcloud '{subcloud_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, subcloud=subcloud_name, local_only=True, with_install=True, release=release, auto_restore=True, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_single_subcloud(subcloud_name=subcloud_name, field_to_watch="deploy_status", in_progress_states=RESTORE_IN_PROGRESS_STATES, complete_state=RESTORE_COMPLETE_STATUS)

    def factory_restore_backup(self, subcloud_name: str) -> None:
        """Factory-restore a subcloud from its factory backup.

        Args:
            subcloud_name (str): Subcloud to restore.
        """
        password = self._get_subcloud_password(subcloud_name)
        get_logger().log_info(f"Factory-restore backup for subcloud '{subcloud_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, subcloud=subcloud_name, factory=True)

    def restore_group_central_backup(self, group_name: str, subcloud_names: List[str], release: str, with_install: bool = True) -> None:
        """Restore a subcloud group from central backups of the given release.

        The release identifies which backup to restore; it is independent of the
        subclouds' current running release. Powers off any duplex members before
        an install-based restore.

        Args:
            group_name (str): Group to restore.
            subcloud_names (List[str]): Subclouds in the group.
            release (str): Release of the backups to restore.
            with_install (bool): If True, reinstall before restoring. Defaults to True.
        """
        password = self._get_subcloud_password(subcloud_names[0])
        for subcloud_name in subcloud_names:
            self._power_off_if_duplex_install(subcloud_name, with_install)
        get_logger().log_info(f"Restore central backup (release {release}) for subcloud group '{group_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, group=group_name, subcloud_list=subcloud_names, release=release, with_install=with_install, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_subclouds(subcloud_names=subcloud_names, field_to_watch="deploy_status", in_progress_states=RESTORE_IN_PROGRESS_STATES, complete_state=RESTORE_COMPLETE_STATUS)

    def restore_group_local_backup(self, group_name: str, subcloud_names: List[str], release: str, with_install: bool = True) -> None:
        """Restore a subcloud group from local backups of the given release.

        The release identifies which backup to restore; it is independent of the
        subclouds' current running release. Powers off any duplex members before
        an install-based restore.

        Args:
            group_name (str): Group to restore.
            subcloud_names (List[str]): Subclouds in the group.
            release (str): Release of the backups to restore.
            with_install (bool): If True, reinstall before restoring. Defaults to True.
        """
        password = self._get_subcloud_password(subcloud_names[0])
        for subcloud_name in subcloud_names:
            self._power_off_if_duplex_install(subcloud_name, with_install)
        get_logger().log_info(f"Restore local backup (release {release}) for subcloud group '{group_name}'")
        self.restore_subcloud_backup(password, self.ssh_connection, group=group_name, subcloud_list=subcloud_names, local_only=True, release=release, with_install=with_install, wait=False)

        DcManagerSubcloudStateWatcherKeywords(self.ssh_connection).watch_subclouds(subcloud_names=subcloud_names, field_to_watch="deploy_status", in_progress_states=RESTORE_IN_PROGRESS_STATES, complete_state=RESTORE_COMPLETE_STATUS)

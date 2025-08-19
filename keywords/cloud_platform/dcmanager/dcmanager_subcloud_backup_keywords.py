from typing import Optional

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals, validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.dcmanager.dcmanager_subcloud_show_keywords import DcManagerSubcloudShowKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords


class DcManagerSubcloudBackupKeywords(BaseKeyword):
    """
    This class contains all the keywords related to the 'dcmanager subcloud-backup <create/delete>' command.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target system.
        """
        self.ssh_connection = ssh_connection

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

    def create_subcloud_backup_expect_fail(
            self,
            sysadmin_password: str,
            con_ssh: SSHConnection,
            subcloud: Optional[str] = None,
            local_only: bool = False,
            backup_yaml: Optional[str] = None, group: Optional[str] = None,
            registry: bool = False,
            subcloud_list: Optional[list] = None,
            expect_cmd_rejection: Optional[bool] = False
    ) -> None:
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

        self.ssh_connection.send(source_openrc(cmd))
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
        check_interval: int = 3,
        timeout: int = 10,
    ) -> None:
        """
        Waits for backup operation to fail

        Args:
            con_ssh (SSHConnection): SSH connection to execute the command (central_ssh or subcloud_ssh).
            subcloud (Optional[str]): The name of the subcloud to check.
            check_interval (int): Time interval (in seconds) to check for file creation. Defaults to 30.
            timeout (int): Maximum time (in seconds) to wait for file creation. Defaults to 600.

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

        validate_equals_with_retry(
            function_to_execute=check_for_failure,
            expected_value=True,
            validation_description="Backup creation failed.",
            timeout=timeout,
            polling_sleep_time=check_interval
        )

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
    ) -> None:
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

        Returns:
            None:
        """

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

    def delete_subcloud_backup(
        self,
        con_ssh: SSHConnection,
        release: str,
        path: Optional[str] = None,
        subcloud: Optional[str] = None,
        local_only: bool = False,
        group: Optional[str] = None,
        sysadmin_password: str = None,
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

        self.ssh_connection.send(source_openrc(cmd))
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
        validate_equals_with_retry(
            function_to_execute=check_backup_deleted,
            expected_value=f"Backup successfully deleted from {path} for {subcloud}",
            validation_description=f"Backup deletion for subcloud {subcloud} completed.",
        )

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

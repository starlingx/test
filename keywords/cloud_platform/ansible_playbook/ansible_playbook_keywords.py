import shlex
from typing import List, Optional

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ansible_playbook.object.ansible_playbook_backup_restore_output import AnsiblePlaybookBackUpRestoreOutput
from keywords.cloud_platform.ansible_playbook.object.backup_size_estimation_object import BackupSizeEstimationObject
from keywords.cloud_platform.ansible_playbook.object.backup_size_estimation_output import BackupSizeEstimationOutput


class AnsiblePlaybookKeywords(BaseKeyword):
    """Provides keyword functions for ansible playbook commands."""

    def __init__(self, ssh_connection: str):
        """Initializes AnsiblePlaybookKeywords with an SSH connection.

        Args:
            ssh_connection (str): SSH connection to the target system.

        """
        self.ssh_connection = ssh_connection

    def ansible_playbook_backup_with_size_estimation(self, backup_dir: str, exclude_dirs: Optional[List[str]] = None, dc_vault_permdir: str = "/opt/dc-vault") -> "BackupSizeEstimationObject":
        """Run the platform backup with ``-vv`` and return the parsed size estimation.

        The playbook is run verbosely so that each ``du`` size-estimation task and
        the free-space pre-check emit structured JSON, which is parsed to verify the
        dc-vault size calculation. The parsed data is taken from the
        playbook stdout captured over the SSH channel; if that is empty it falls back
        to the tail of the ansible log file.

        Args:
            backup_dir (str): Destination backup directory (e.g. "/opt/backups").
            exclude_dirs (Optional[List[str]]): Directories to pass to ``exclude_dirs``. Defaults to None.
            dc_vault_permdir (str): The dc-vault path the playbook measures. Defaults to "/opt/dc-vault".

        Returns:
            BackupSizeEstimationObject: Parsed size-estimation values from the run.
        """
        backup_playbook_path = "/usr/share/ansible/stx-ansible/playbooks/backup.yml"
        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

        exclude_dirs_argument = ""
        if exclude_dirs:
            exclude_dirs_value = ",".join(exclude_dirs)
            exclude_dirs_argument = f'-e {shlex.quote(f"exclude_dirs={exclude_dirs_value}")}'

        command = f'ansible-playbook -vv {backup_playbook_path} -e "ansible_become_pass={admin_password}" -e "admin_password={admin_password}" -e "backup_dir={backup_dir}" {exclude_dirs_argument}'

        cmd_out = self.ssh_connection.send(command, command_timeout=1800, reconnect_timeout=1800)
        self.validate_success_return_code(self.ssh_connection)

        log_lines = cmd_out if cmd_out else []
        estimation = BackupSizeEstimationOutput(log_lines, dc_vault_permdir=dc_vault_permdir).get_backup_size_estimation()

        # Fall back to the ansible log file if the console capture was truncated.
        if not estimation.is_complete():
            get_logger().log_info("Console capture incomplete, reading ansible log for size estimation")
            log_file_lines = self.ssh_connection.send("cat ~/ansible.log")
            estimation = BackupSizeEstimationOutput(log_file_lines, dc_vault_permdir=dc_vault_permdir).get_backup_size_estimation()

        get_logger().log_info(f"Parsed backup size estimation: {estimation}")
        return estimation

    def ansible_playbook_backup(self, backup_dir: str, backup_registry: bool = False, platform_backup_filename_prefix: str = None, exclude_dirs: Optional[List[str]] = None, verbose: bool = False) -> bool:
        """
        Executes the `ansible-playbook` backup command and returns the parsed output.

        Args:
            backup_dir (str): backup playbook path
            backup_registry (bool): backup registry
            platform_backup_filename_prefix (str): prefix for the backup filename
            exclude_dirs (Optional[List[str]]): directories to pass to the playbook's
                ``exclude_dirs`` option (comma-joined). Defaults to None.
            verbose (bool): run the playbook with ``-vv`` so per-task module input
                (du commands) and stdout are captured in the ansible log. Defaults to False.

        Returns:
            bool: Parsed output to verify successful backup
        """
        backup_playbook_path = "/usr/share/ansible/stx-ansible/playbooks/backup.yml"
        backup_registry_argument = ""
        if backup_registry:
            backup_registry_argument = '-e "backup_registry_filesystem=true"'

        prefix_argument = ""
        if platform_backup_filename_prefix:
            prefix_argument = f'-e "platform_backup_filename_prefix={platform_backup_filename_prefix}"'

        exclude_dirs_argument = ""
        if exclude_dirs:
            exclude_dirs_value = ",".join(exclude_dirs)
            exclude_dirs_argument = f'-e {shlex.quote(f"exclude_dirs={exclude_dirs_value}")}'

        verbose_argument = "-vv" if verbose else ""

        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

        command = f'ansible-playbook {verbose_argument} {backup_playbook_path} -e "ansible_become_pass={admin_password}" -e "admin_password={admin_password}" -e "backup_dir={backup_dir}" {backup_registry_argument} {prefix_argument} {exclude_dirs_argument}'

        cmd_out = self.ssh_connection.send(command, command_timeout=1200, reconnect_timeout=1200)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("get ansible playbook backup output")
        backup_output = AnsiblePlaybookBackUpRestoreOutput(cmd_out)
        return backup_output.validate_ansible_playbook_backup_restore_result()

    def ansible_playbook_restore(self, backup_dir: str, restore_mode: str = None, restore_registry: bool = False) -> bool:
        """
        Executes the ansible-playbook restore command

        Args:
            backup_dir (str): Directory where backup file is stored
            restore_mode (str): Restore mode (default: None)
            restore_registry (bool): Whether to restore the registry filesystem

        Returns:
            bool: True if restore succeeded
        """
        restore_playbook_path = "/usr/share/ansible/stx-ansible/playbooks/restore_platform.yml"
        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()
        restore_registry_arg = '-e "restore_registry_filesystem=true"' if restore_registry else ""
        restore_mode_arg = f'-e "restore_mode={restore_mode}" ' if restore_mode else ""

        # Get the latest backup file
        cmd = f"ls {backup_dir}/*_platform_backup_*.tgz | tail -n 1 | xargs basename"
        backup_filename = self.ssh_connection.send(cmd)[0].strip()

        command = f"ansible-playbook {restore_playbook_path} " f'-e "ansible_become_pass={admin_password}" ' f'-e "admin_password={admin_password}" ' f'-e "initial_backup_dir={backup_dir}" ' f'-e "backup_filename={backup_filename}" ' f"{restore_mode_arg}" f"{restore_registry_arg}"

        cmd_out = self.ssh_connection.send(command, command_timeout=2100, reconnect_timeout=2100)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("get ansible playbook restore output")
        restore_output = AnsiblePlaybookBackUpRestoreOutput(cmd_out)
        return restore_output.validate_ansible_playbook_backup_restore_result()

    def get_latest_platform_backup_tarball(self, backup_dir: str, filename_substring: str = "_platform_backup_") -> str:
        """Return the full path of the most recent backup tarball in a directory.

        Lists the directory one entry per line (``ls -1t``) and matches
        ``*{filename_substring}*.tgz`` in Python. Shell glob expansion is avoided
        because it does not expand reliably through the non-interactive sudo
        exec path, and a plain ``ls`` of a directory can place multiple names on
        one line, breaking substring matching. The System Controller backup
        produces both a platform (``_platform_backup_``) and a dc-vault
        (``_dc_vault_backup_``) tarball; pass ``filename_substring`` to select which.

        Args:
            backup_dir (str): Directory that holds the backup tarballs.
            filename_substring (str): Substring the tarball name must contain.
                Defaults to "_platform_backup_".

        Returns:
            str: Absolute path to the latest matching tarball, or an empty
            string if no matching tarball exists.
        """
        output = self.ssh_connection.send_as_sudo_non_interactive(f"ls -1t {shlex.quote(backup_dir)}")
        for line in output:
            candidate = line.strip()
            if candidate.endswith(".tgz") and filename_substring in candidate:
                return f"{backup_dir}/{candidate}"
        return ""

    def delete_platform_backup_tarball(self, backup_tarball_path: str) -> None:
        """Delete a specific platform backup tarball.

        Args:
            backup_tarball_path (str): Absolute path to the tarball to delete.
        """
        if not backup_tarball_path:
            return
        self.ssh_connection.send_as_sudo_non_interactive(f"rm -f {shlex.quote(backup_tarball_path)}")

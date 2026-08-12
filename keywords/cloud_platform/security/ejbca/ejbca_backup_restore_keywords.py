from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class EjbcaBackupRestoreKeywords(BaseKeyword):
    """Keywords for EJBCA backup and restore operations."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize backup/restore keywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to active controller.
        """
        self.ssh_connection = ssh_connection

    def run_backup_playbook(self, playbook_path: str, backup_dir: str) -> str:
        """Run EJBCA backup ansible playbook.

        Args:
            playbook_path (str): Path to ejbca_backup.yml playbook.
            backup_dir (str): Directory to store backup tarball.

        Returns:
            str: Playbook output.
        """
        get_logger().log_info(f"Running EJBCA backup: {playbook_path}")
        cmd = f"ansible-playbook {playbook_path} -e 'initial_backup_dir={backup_dir}'"
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return output

    def run_restore_playbook(self, playbook_path: str, backup_dir: str, backup_filename: str) -> str:
        """Run EJBCA restore ansible playbook.

        Args:
            playbook_path (str): Path to ejbca_restore.yml playbook.
            backup_dir (str): Directory containing backup tarball.
            backup_filename (str): Name of the backup file to restore.

        Returns:
            str: Playbook output.
        """
        get_logger().log_info(f"Running EJBCA restore: {playbook_path}")
        cmd = (
            f"ansible-playbook {playbook_path} "
            f"-e 'initial_backup_dir={backup_dir}' "
            f"-e 'backup_filename={backup_filename}'"
        )
        output = self.ssh_connection.send_as_sudo(cmd)
        self.validate_success_return_code(self.ssh_connection)
        return output

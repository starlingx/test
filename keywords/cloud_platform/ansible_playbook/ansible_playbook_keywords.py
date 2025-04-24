from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.ansible_playbook.object.ansible_playbook_backup_output import AnsiblePlaybookBackUpOutput


class AnsiblePlaybookKeywords(BaseKeyword):
    """Provides keyword functions for ansible playbook commands."""

    def __init__(self, ssh_connection: str):
        """Initializes AnsiblePlaybookKeywords with an SSH connection.

        Args:
            ssh_connection (str): SSH connection to the target system.

        """
        self.ssh_connection = ssh_connection

    def ansible_playbook_backup(self, backup_dir: str, backup_registry: bool = False) -> bool:
        """
        Executes the `ansible-playbook` backup command and returns the parsed output.

        Args:
            backup_dir (str): backuo playbook path
            backup_registry (bool): backup registry

        Returns:
            bool: Parsed output to verify successful backup
        """
        backup_playbook_path = "/usr/share/ansible/stx-ansible/playbooks/backup.yml"
        backup_registry_argument = ""
        if backup_registry:
            backup_registry_argument = '-e "backup_registry_filesystem=true"'

        admin_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

        command = f'ansible-playbook {backup_playbook_path} -e "ansible_become_pass={admin_password}" -e "admin_password={admin_password}" -e "backup_dir={backup_dir}" {backup_registry_argument}'
        cmd_out = self.ssh_connection.send(command, reconnect_timeout=3600)
        self.validate_success_return_code(self.ssh_connection)
        get_logger().log_info("get ansible playbook backup output")
        backup_output = AnsiblePlaybookBackUpOutput(cmd_out)
        backup_output.validate_ansible_playbook_backup_result()
        return backup_output

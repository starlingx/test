"""Keywords for LDAP user management via manage_local_ldap_account.yml playbook."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class LdapKeywords(BaseKeyword):
    """Manage LDAP users via the manage_local_ldap_account.yml ansible playbook.

    This is the recommended approach for creating LDAP users on StarlingX.
    The playbook handles password setup, expiry, and pwdReset properly,
    unlike ldapusersetup which forces password change on first login.
    """

    PLAYBOOK_PATH = "/usr/share/ansible/stx-ansible/playbooks/manage_local_ldap_account.yml"
    INVENTORY_PATH = "secure-inventory"
    USER_BASE_DN = "ou=People,dc=cgcs,dc=local"
    BIND_DN = "CN=ldapadmin,DC=cgcs,DC=local"

    def __init__(self, ssh_connection: SSHConnection, ansible_password: str) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller (as sysadmin).
            ansible_password (str): Sysadmin password for ansible_password, ansible_become_pass, and vault.
        """
        self.ssh_connection = ssh_connection
        self.ansible_password = ansible_password

    def ensure_secure_inventory(self) -> None:
        """Create and vault-encrypt the secure-inventory file if not present."""
        content = f"[all:vars]\n" f"ansible_user=sysadmin\n" f"ansible_password={self.ansible_password}\n" f"ansible_become_pass={self.ansible_password}\n" f"\n" f"[systemcontroller]\n" f"systemcontroller-0 ansible_host=127.0.0.1\n"
        self.ssh_connection.send(f"cat > {self.INVENTORY_PATH} << 'INVEOF'\n{content}INVEOF")
        prompts = [
            PromptResponse("New Vault password:", self.ansible_password),
            PromptResponse("Confirm New Vault password:", self.ansible_password),
            PromptResponse("~$", None),
        ]
        self.ssh_connection.send_expect_prompts(f"ansible-vault encrypt {self.INVENTORY_PATH}", prompts)

    def create_user(self, username: str, password: str, user_role: str = "admin") -> None:
        """Create an LDAP user via the manage_local_ldap_account playbook.

        Cleans up any existing LDAP and Keystone user first to ensure idempotent creation.

        Args:
            username (str): Username to create.
            password (str): Password for the new user.
            user_role (str): Role for the user (admin, reader, operator, configurator).
        """
        get_logger().log_info(f"Creating LDAP user via playbook: {username} (role={user_role})")
        self.ensure_secure_inventory()
        self.run_playbook("delete", username)
        self.ssh_connection.send(source_openrc(f"openstack user delete {username}"))
        self.ssh_connection.send(f"echo '{self.ansible_password}' | sudo -S rm -rf /home/{username}")
        self.run_playbook("create", username, password, user_role)

    def run_playbook(self, mode: str, username: str, password: str = None, user_role: str = None) -> None:
        """Run the manage_local_ldap_account playbook.

        Args:
            mode (str): 'create' or 'delete'.
            username (str): LDAP username.
            password (str): User password (only for create mode).
            user_role (str): User role (only for create mode).

        Raises:
            KeywordException: If the playbook fails (failed != 0 in output).
        """
        extra = f"mode={mode} user_id={username}"
        if mode == "create" and user_role:
            extra += f" user_role={user_role} sys_protected=yes sudo_permission=yes"
        cmd = f"ansible-playbook --verbose --inventory {self.INVENTORY_PATH} --ask-vault-pass --extra-vars='{extra}' {self.PLAYBOOK_PATH}"
        prompts = [PromptResponse("Vault password:", self.ansible_password)]
        if mode == "create":
            prompts.append(PromptResponse("password for the user", password))
        prompts.append(PromptResponse("~$", None))
        output = self.ssh_connection.send_expect_prompts(cmd, prompts, command_timeout=120)
        raw = "\n".join(output) if isinstance(output, list) else (output or "")
        if mode == "create" and "failed=0" not in raw:
            raise KeywordException(f"Ansible playbook failed to {mode} user {username}. Output: {raw[-200:]}")

    def delete_user(self, username: str) -> None:
        """Delete an LDAP user via the manage_local_ldap_account playbook.

        Args:
            username (str): Username to delete.
        """
        get_logger().log_info(f"Deleting LDAP user via playbook: {username}")
        self.ensure_secure_inventory()
        extra = f"mode=delete user_id={username}"
        cmd = f"ansible-playbook --verbose --inventory {self.INVENTORY_PATH} --ask-vault-pass --extra-vars='{extra}' {self.PLAYBOOK_PATH}"
        prompts = [
            PromptResponse("Vault password:", self.ansible_password),
            PromptResponse("~$", None),
        ]
        self.ssh_connection.send_expect_prompts(cmd, prompts, command_timeout=120)

    def create_group(self, group_name: str) -> None:
        """Create an LDAP group via sudo ldapaddgroup.

        Args:
            group_name (str): Group name to create.
        """
        get_logger().log_info(f"Creating LDAP group: {group_name}")
        self.ssh_connection.send(f"echo '{self.ansible_password}' | sudo -S ldapaddgroup {group_name}")
        self.validate_success_return_code(self.ssh_connection)

    def add_user_to_group(self, username: str, group_name: str) -> None:
        """Add an LDAP user to a group via sudo ldapaddusertogroup.

        Args:
            username (str): Username to add.
            group_name (str): Group to add the user to.
        """
        get_logger().log_info(f"Adding LDAP user {username} to group {group_name}")
        self.ssh_connection.send(f"echo '{self.ansible_password}' | sudo -S ldapaddusertogroup {username} {group_name}")
        self.validate_success_return_code(self.ssh_connection)

    def delete_group(self, group_name: str) -> None:
        """Delete an LDAP group via sudo ldapdeletegroup.

        Args:
            group_name (str): Group name to delete.
        """
        get_logger().log_info(f"Deleting LDAP group: {group_name}")
        self.ssh_connection.send(f"echo '{self.ansible_password}' | sudo -S ldapdeletegroup {group_name}")

    def add_mail_attribute(self, username: str, email: str) -> None:
        """Add mail attribute to an existing LDAP user via ldapmodify.

        Args:
            username (str): LDAP username.
            email (str): Email address to set.
        """
        get_logger().log_info(f"Adding mail attribute '{email}' to LDAP user '{username}'")
        ldif = f"dn: uid={username},{self.USER_BASE_DN}\nchangetype: modify\nreplace: mail\nmail: {email}"
        cmd = f"echo '{self.ansible_password}' | sudo -S ldapmodify -x -D '{self.BIND_DN}' -w $(echo '{self.ansible_password}') << 'EOF'\n{ldif}\nEOF"
        self.ssh_connection.send(cmd)
        self.validate_success_return_code(self.ssh_connection)

    def verify_mail_attribute(self, username: str) -> str:
        """Query LDAP and return the mail attribute for a user.

        Args:
            username (str): LDAP username.

        Returns:
            str: Mail attribute value, or empty string if not set.
        """
        get_logger().log_info(f"Querying mail attribute for LDAP user '{username}'")
        cmd = f"ldapsearch -x -b '{self.USER_BASE_DN}' '(uid={username})' mail"
        output = self.ssh_connection.send(cmd)
        for line in output.split("\n") if isinstance(output, str) else output:
            if line.startswith("mail:"):
                return line.split(":", 1)[1].strip()
        return ""

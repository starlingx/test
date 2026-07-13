"""Keywords for LDAP user management via manage_local_ldap_account.yml playbook."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.linux.keyring.keyring_keywords import KeyringKeywords


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
        Verifies the user exists in LDAP after playbook execution, and falls back to
        ldapadduser if the playbook didn't actually create the LDAP entry.

        Args:
            username (str): Username to create.
            password (str): Password for the new user.
            user_role (str): Role for the user (admin, reader, operator, configurator).
        """
        get_logger().log_info(f"Creating LDAP user via playbook: {username} (role={user_role})")
        self.ensure_secure_inventory()
        self.run_playbook("delete", username)
        self.ssh_connection.send(source_openrc(f"openstack user delete {username}"))
        self.ssh_connection.send_as_sudo(f"rm -rf /home/{username}")
        self.run_playbook("create", username, password, user_role)
        # Remove home dir created by playbook (may have wrong UID from SSSD cache).
        # The user's next SSH login will recreate it with correct ownership.
        self.ssh_connection.send_as_sudo(f"rm -rf /home/{username}")

        # Verify user exists in LDAP — playbook may report success without creating the entry
        if not self._user_exists_in_ldap(username):
            get_logger().log_info(f"User '{username}' not found in LDAP after playbook. Creating via ldapadd fallback.")
            self._create_user_via_ldapadd(username, password)
            if not self._user_exists_in_ldap(username):
                raise KeywordException(f"Failed to create LDAP user '{username}' — not found in directory after all attempts")
        else:
            # User exists — ensure password is set for LDAP simple bind (Dex compatibility)
            self._force_set_password(username, password)

    def _user_exists_in_ldap(self, username: str) -> bool:
        """Check if an LDAP user entry exists in the directory.

        Args:
            username (str): LDAP username to check.

        Returns:
            bool: True if user exists in LDAP directory.
        """
        ldap_admin_pw = KeyringKeywords(self.ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
        user_dn = f"uid={username},{self.USER_BASE_DN}"
        cmd = f"ldapsearch -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' -b '{user_dn}' -s base '(objectClass=*)' dn 2>/dev/null | grep -q 'dn:'"
        self.ssh_connection.send(cmd)
        rc = self.ssh_connection.get_return_code()
        exists = rc == 0
        get_logger().log_info(f"LDAP user '{username}' exists in directory: {exists}")
        return exists

    def _create_user_via_ldapadd(self, username: str, password: str) -> None:
        """Create an LDAP user directly via ldapadd with a complete LDIF entry.

        Fallback when the ansible playbook fails to create the user. Creates a
        posixAccount with all required attributes for Dex LDAP connector
        (objectClass=posixAccount filter). Sets password via ldappasswd
        (password modify extended operation) which properly processes it
        through OpenLDAP's ppolicy overlay.

        Args:
            username (str): LDAP username.
            password (str): User password.
        """
        get_logger().log_info(f"Creating LDAP user '{username}' via ldapadd with full LDIF")
        ldap_admin_pw = KeyringKeywords(self.ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
        user_dn = f"uid={username},{self.USER_BASE_DN}"

        # Get next available uidNumber
        cmd = f"ldapsearch -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' -b '{self.USER_BASE_DN}' '(objectClass=posixAccount)' uidNumber 2>/dev/null | grep uidNumber | awk '{{print $2}}' | sort -n | tail -1"
        output = self.ssh_connection.send(cmd)
        raw = "\n".join(output) if isinstance(output, list) else str(output)
        try:
            next_uid = int(raw.strip().split("\n")[-1]) + 1
        except (ValueError, IndexError):
            next_uid = 10000

        # Create user entry WITHOUT userPassword (will set via ldappasswd after)
        ldif = f"dn: {user_dn}\n" f"objectClass: inetOrgPerson\n" f"objectClass: posixAccount\n" f"objectClass: shadowAccount\n" f"uid: {username}\n" f"cn: {username}\n" f"sn: {username}\n" f"uidNumber: {next_uid}\n" f"gidNumber: 100\n" f"homeDirectory: /home/{username}\n" f"loginShell: /bin/bash"

        cmd = f"ldapadd -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' << 'LDIFEOF'\n{ldif}\nLDIFEOF"
        self.ssh_connection.send_as_sudo(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc != 0:
            get_logger().log_info(f"ldapadd returned rc={rc} — entry may already exist, continuing to set password")

        # Set password via ldappasswd (password modify extended op) — this respects ppolicy
        cmd = f"ldappasswd -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' -s '{password}' '{user_dn}'"
        self.ssh_connection.send_as_sudo(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc == 0:
            get_logger().log_info(f"LDAP user '{username}' created and password set via ldappasswd (uid={next_uid})")
        else:
            get_logger().log_info(f"ldappasswd returned rc={rc} — password may not be set correctly")

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
            prompts.append(PromptResponse("What is the password for the user account?", password if password else self.ansible_password))
        prompts.append(PromptResponse("~$", None))
        output = self.ssh_connection.send_expect_prompts(cmd, prompts, command_timeout=180)
        raw = "\n".join(output) if isinstance(output, list) else (output or "")
        if mode == "create":
            if "failed=0" not in raw:
                raise KeywordException(f"Ansible playbook failed to {mode} user {username}. Output: {raw[-200:]}")
            # Always force-set password after create — newer builds no longer
            # prompt for password interactively during playbook execution.
            self._force_set_password(username, password)
        elif mode == "delete" and "failed=0" not in raw:
            get_logger().log_info(f"LDAP delete playbook had non-zero failed count for {username} (may not exist). Continuing.")

    def _force_set_password(self, username: str, password: str) -> None:
        """Force set LDAP user password via ldappasswd for Dex LDAP bind compatibility.

        Uses the LDAP Password Modify Extended Operation (ldappasswd) which
        properly processes the password through OpenLDAP's ppolicy overlay.

        On builds with ppolicy `pwdMustChange`, admin-set passwords require
        the user to change on first bind. We work around this by setting a
        temporary password first (to satisfy the "not reusing" constraint),
        then setting the final password, which clears the mustChange state.

        Args:
            username (str): LDAP username.
            password (str): Password to set.
        """
        get_logger().log_info(f"Setting password for '{username}' via ldappasswd (extended operation)")
        ldap_admin_pw = KeyringKeywords(self.ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
        user_dn = f"uid={username},{self.USER_BASE_DN}"

        # Set temporary password first (to avoid "not being changed from existing" constraint)
        temp_pw = "T3mp0r@ryPw!999"
        cmd = f"ldappasswd -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' -s '{temp_pw}' '{user_dn}'"
        self.ssh_connection.send_as_sudo(cmd)

        # Now set the real password (satisfies password history constraint)
        cmd = f"ldappasswd -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' -s '{password}' '{user_dn}'"
        self.ssh_connection.send_as_sudo(cmd)
        rc = self.ssh_connection.get_return_code()
        if rc == 0:
            get_logger().log_info(f"Password set successfully for '{username}'")
        else:
            get_logger().log_info(f"ldappasswd returned rc={rc} for '{username}'")

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
        self.ssh_connection.send_as_sudo(f"ldapaddgroup {group_name}")
        self.validate_success_return_code(self.ssh_connection)

    def add_user_to_group(self, username: str, group_name: str) -> None:
        """Add an LDAP user to a group via sudo ldapaddusertogroup.

        Args:
            username (str): Username to add.
            group_name (str): Group to add the user to.
        """
        get_logger().log_info(f"Adding LDAP user {username} to group {group_name}")
        self.ssh_connection.send_as_sudo(f"ldapaddusertogroup {username} {group_name}")
        self.validate_success_return_code(self.ssh_connection)

    def delete_group(self, group_name: str) -> None:
        """Delete an LDAP group via sudo ldapdeletegroup.

        Args:
            group_name (str): Group name to delete.
        """
        get_logger().log_info(f"Deleting LDAP group: {group_name}")
        self.ssh_connection.send_as_sudo(f"ldapdeletegroup {group_name}")

    def add_mail_attribute(self, username: str, email: str) -> None:
        """Add mail attribute to an existing LDAP user via ldapmodify.

        Args:
            username (str): LDAP username.
            email (str): Email address to set.
        """
        get_logger().log_info(f"Adding mail attribute '{email}' to LDAP user '{username}'")
        ldap_admin_pw = KeyringKeywords(self.ssh_connection).get_keyring(service="ldap", identifier="ldapadmin")
        ldif = f"dn: uid={username},{self.USER_BASE_DN}\nchangetype: modify\nreplace: mail\nmail: {email}"
        cmd = f"ldapmodify -x -D '{self.BIND_DN}' -w '{ldap_admin_pw}' << 'EOF'\n{ldif}\nEOF"
        self.ssh_connection.send_as_sudo(cmd)
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

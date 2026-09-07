import json
import shlex

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class DockerConfigKeywords(BaseKeyword):
    """Keywords for managing the Docker client credential file (config.json).

    The Docker CLI persists registry credentials to ``config.json`` (default
    ``/var/rootdirs/root/.docker/config.json`` on WRCP hosts). This class provides
    reusable operations to inspect, seed, corrupt, back up, and restore that file
    so tests can simulate stale/expired registry credentials without touching the
    real credentials permanently.

    All privileged operations use ``send_as_sudo_non_interactive`` because the
    WRCP shell prompt contains ``@`` (e.g. ``sysadmin@controller-0``), which the
    interactive ``send_as_sudo`` path treats as a command-complete marker and
    mismatches. The non-interactive path feeds the sudo password via stdin and
    runs through ``exec_command``, avoiding that fragility.
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize DockerConfigKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def config_exists(self, config_path: str) -> bool:
        """Check whether the Docker config.json exists on the host.

        Args:
            config_path (str): Absolute path to the Docker config.json.

        Returns:
            bool: True if the file exists, False otherwise.
        """
        output = self.ssh_connection.send_as_sudo_non_interactive(f"test -f {shlex.quote(config_path)} && echo EXISTS || echo MISSING")
        return "EXISTS" in "".join(output)

    def read_config(self, config_path: str) -> str:
        """Read the raw contents of the Docker config.json.

        Args:
            config_path (str): Absolute path to the Docker config.json.

        Returns:
            str: The file contents joined into a single string.
        """
        return "".join(self.ssh_connection.send_as_sudo_non_interactive(f"cat {shlex.quote(config_path)}"))

    def backup_config(self, config_path: str, backup_path: str) -> bool:
        """Copy the Docker config.json to a backup location.

        Args:
            config_path (str): Absolute path to the Docker config.json.
            backup_path (str): Absolute path where the backup copy is written.

        Returns:
            bool: True if the backup copy exists after the operation, False otherwise.
        """
        self.ssh_connection.send_as_sudo_non_interactive(f"cp {shlex.quote(config_path)} {shlex.quote(backup_path)}")
        return self.config_exists(backup_path)

    def restore_config(self, backup_path: str, config_path: str) -> bool:
        """Restore the Docker config.json from a backup copy.

        Args:
            backup_path (str): Absolute path to the backup copy.
            config_path (str): Absolute path to the Docker config.json to restore.

        Returns:
            bool: True if the config.json exists after restore, False otherwise.
        """
        self.ssh_connection.send_as_sudo_non_interactive(f"cp {shlex.quote(backup_path)} {shlex.quote(config_path)}")
        return self.config_exists(config_path)

    def delete_config(self, config_path: str) -> bool:
        """Delete the Docker config.json.

        Args:
            config_path (str): Absolute path to the Docker config.json.

        Returns:
            bool: True if the file no longer exists after deletion, False otherwise.
        """
        self.ssh_connection.send_as_sudo_non_interactive(f"rm -f {shlex.quote(config_path)}")
        return not self.config_exists(config_path)

    def seed_config_with_auth(self, config_path: str, registry_url: str, auth_token: str) -> bool:
        """Write a Docker config.json containing a single registry auth entry.

        Used to guarantee a credential file exists before a backup so the
        backup-exclusion assertion is meaningful (the file must be present with
        credentials, otherwise there is nothing to exclude).

        Args:
            config_path (str): Absolute path to the Docker config.json.
            registry_url (str): Registry URL key under the ``auths`` object.
            auth_token (str): Base64-style ``auth`` token value for the registry.

        Returns:
            bool: True if the config.json exists after writing, False otherwise.
        """
        config_dir = config_path.rsplit("/", 1)[0]
        self.ssh_connection.send_as_sudo_non_interactive(f"mkdir -p {shlex.quote(config_dir)}")
        content = json.dumps({"auths": {registry_url: {"auth": auth_token}}})
        # Write through `bash -c` so the redirect runs inside the root shell. The
        # non-interactive sudo path pipes the password to stdin, so a heredoc
        # cannot be used (it would collide with the password on stdin); passing
        # the content as a printf argument avoids stdin entirely.
        inner = f"printf %s {shlex.quote(content)} > {shlex.quote(config_path)}"
        self.ssh_connection.send_as_sudo_non_interactive(f"bash -c {shlex.quote(inner)}")
        return self.config_exists(config_path)

    def corrupt_auth_field(self, config_path: str, suffix: str = "X") -> str:
        """Corrupt the credential token(s) in config.json to simulate stale creds.

        Appends a suffix to every ``auth`` and ``identitytoken`` value in the file,
        which invalidates the base64 credential exactly as described in the test
        plan (``illegal base64 data`` / ``unauthorized`` on pull).

        Args:
            config_path (str): Absolute path to the Docker config.json.
            suffix (str): Characters appended to each token value. Defaults to "X".

        Returns:
            str: The corrupted config.json contents after modification.
        """
        get_logger().log_info(f"Corrupting auth/identitytoken values in {config_path}")
        # Append the suffix to the value of any "auth" or "identitytoken" JSON field.
        sed_expr = f's/\\("\\(auth\\|identitytoken\\)"[[:space:]]*:[[:space:]]*"[^"]*\\)"/\\1{suffix}"/g'
        self.ssh_connection.send_as_sudo_non_interactive(f"sed -i {shlex.quote(sed_expr)} {shlex.quote(config_path)}")
        return self.read_config(config_path)

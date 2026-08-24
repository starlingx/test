import shlex

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword

ETCD_STAGE0_SYMLINK_PATH = "/var/lib/etcd/stage0"


class EtcdKeywords(BaseKeyword):
    """Keywords for etcd version inspection via the stage0 symlink."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize EtcdKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the active controller.
        """
        self.ssh_connection = ssh_connection

    def get_etcd_version(self) -> str:
        """Get the etcd version from the /var/lib/etcd/stage0 symlink target.

        Reads the symlink at /var/lib/etcd/stage0 and extracts the version
        from the target path. For example, if the symlink points to
        /var/lib/etcd/etcd-3.5.15/stage0, this returns 'etcd-3.5.15'.

        Returns:
            str: The etcd version directory name (e.g. 'etcd-3.5.15').
        """
        output = self.ssh_connection.send(f"readlink -f {shlex.quote(ETCD_STAGE0_SYMLINK_PATH)}")
        self.validate_success_return_code(self.ssh_connection)

        resolved_path = output.strip() if isinstance(output, str) else output[0].strip()
        # Path looks like /var/lib/etcd/etcd-3.5.15/stage0 — version is the parent dir name
        version = resolved_path.rsplit("/", 2)[-2]
        get_logger().log_info(f"Etcd version from symlink: {version}")
        return version

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.linux.which.which_keywords import WhichKeywords


class KubeloginInstallKeywords(BaseKeyword):
    """Keywords for installing kubectl and the kubelogin oidc-login plugin."""

    KUBECTL_INSTALL_PATH = "/usr/local/bin/kubectl"
    KUBELOGIN_INSTALL_PATH = "/usr/local/bin/kubectl-oidc_login"

    def __init__(self, ssh_connection: SSHConnection):
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host.
        """
        self.ssh_connection = ssh_connection
        self.which_keywords = WhichKeywords(ssh_connection)

    def is_kubectl_installed(self) -> bool:
        """Check if kubectl is available in PATH.

        Returns:
            bool: True if installed, False otherwise.
        """
        try:
            self.which_keywords.which_process("kubectl")
            return True
        except Exception:
            return False

    def is_kubelogin_installed(self) -> bool:
        """Check if kubectl-oidc_login plugin is available in PATH.

        Returns:
            bool: True if installed, False otherwise.
        """
        try:
            self.which_keywords.which_process("kubectl-oidc_login")
            return True
        except Exception:
            return False

    def install_kubectl(self, download_url: str) -> None:
        """Download and install kubectl standalone binary if not already present.

        Args:
            download_url (str): URL to the kubectl binary.
        """
        if self.is_kubectl_installed():
            get_logger().log_info("kubectl is already installed, skipping")
            return

        get_logger().log_info(f"Installing kubectl from {download_url}")
        self.ssh_connection.send(f"curl -sSL -o /tmp/kubectl {download_url}")
        self.validate_success_return_code(self.ssh_connection)

        self.ssh_connection.send_as_sudo(f"install -m 0755 /tmp/kubectl {self.KUBECTL_INSTALL_PATH}")
        self.validate_success_return_code(self.ssh_connection)

        self.ssh_connection.send("rm -f /tmp/kubectl")
        get_logger().log_info(f"kubectl installed at {self.KUBECTL_INSTALL_PATH}")

    def install_kubelogin(self, download_url: str, working_dir: str) -> None:
        """Download and install the kubelogin kubectl-oidc_login plugin if not already present.

        Downloads the zip archive from GitHub releases, extracts the kubelogin
        binary, and installs it as kubectl-oidc_login in /usr/local/bin so
        kubectl can discover it as a plugin.

        Args:
            download_url (str): URL to the kubelogin zip archive.
            working_dir (str): Working directory on the remote host for temp files.
        """
        if self.is_kubelogin_installed():
            get_logger().log_info("kubectl-oidc_login is already installed, skipping")
            return

        get_logger().log_info(f"Installing kubectl-oidc_login from {download_url}")
        zip_path = f"{working_dir}kubelogin.zip"
        extract_dir = f"{working_dir}kubelogin_extracted"

        self.ssh_connection.send(f"curl -sSL -o {zip_path} {download_url}")
        self.validate_success_return_code(self.ssh_connection)

        self.ssh_connection.send(f"unzip -o {zip_path} -d {extract_dir}")
        self.validate_success_return_code(self.ssh_connection)

        self.ssh_connection.send_as_sudo(f"install -m 0755 {extract_dir}/kubelogin {self.KUBELOGIN_INSTALL_PATH}")
        self.validate_success_return_code(self.ssh_connection)

        self.ssh_connection.send(f"rm -rf {zip_path} {extract_dir}")
        get_logger().log_info(f"kubectl-oidc_login installed at {self.KUBELOGIN_INSTALL_PATH}")

    def install_all(self, kubectl_download_url: str, kubelogin_download_url: str, working_dir: str) -> None:
        """Install both kubectl and kubelogin plugin.

        Args:
            kubectl_download_url (str): URL to the kubectl binary.
            kubelogin_download_url (str): URL to the kubelogin zip archive.
            working_dir (str): Working directory on the remote host for temp files.
        """
        self.install_kubectl(kubectl_download_url)
        self.install_kubelogin(kubelogin_download_url, working_dir)

from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc


class HelmReleaseKeywords(BaseKeyword):
    """Keywords for Helm CLI release operations (helm ls, helm uninstall)."""

    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection

    def helm_ls(self, namespace: str = None, all_namespaces: bool = False) -> str:
        """Run 'helm ls' and return raw output.

        Args:
            namespace (str): Specific namespace to list releases from.
            all_namespaces (bool): If True, list releases across all namespaces.

        Returns:
            str: Raw output from helm ls.
        """
        cmd = "helm ls"
        if all_namespaces:
            cmd += " -A"
        elif namespace:
            cmd += f" -n {namespace}"

        output = self.ssh_connection.send_as_sudo(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else str(output)

    def is_release_present(self, release_name: str, namespace: str = None) -> bool:
        """Check if a helm release is present.

        Args:
            release_name (str): Name of the helm release.
            namespace (str): Namespace to check. If None, checks all namespaces.

        Returns:
            bool: True if the release exists.
        """
        output = self.helm_ls(namespace=namespace, all_namespaces=(namespace is None))
        return release_name in output

    def wait_for_release_present(self, release_name: str, namespace: str = None, timeout: int = 300) -> None:
        """Wait for a helm release to appear in 'helm ls'.

        Args:
            release_name (str): Name of the helm release.
            namespace (str): Namespace to check. If None, checks all namespaces.
            timeout (int): Timeout in seconds.
        """
        validate_equals_with_retry(
            lambda: self.is_release_present(release_name, namespace),
            True,
            f"Helm release '{release_name}' is present",
            timeout=timeout,
        )

    def helm_uninstall(self, release_name: str, namespace: str) -> str:
        """Run 'helm uninstall <release_name> -n <namespace>'.

        Args:
            release_name (str): Name of the helm release to uninstall.
            namespace (str): Namespace of the release.

        Returns:
            str: Output from helm uninstall.
        """
        cmd = f"helm uninstall {release_name} -n {namespace}"
        output = self.ssh_connection.send_as_sudo(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return "\n".join(output) if isinstance(output, list) else str(output)

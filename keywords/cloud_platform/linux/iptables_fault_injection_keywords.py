from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class IptablesFaultInjectionKeywords(BaseKeyword):
    """Keywords for injecting and removing iptables/ip6tables DROP rules.

    Used to simulate connectivity failures (e.g. blocking the Kubernetes API
    server port during a control-plane upgrade to trigger a VIM auto-rollback).

    The rules are applied on the host reachable via the provided SSH connection,
    so the same class works against the system controller or a subcloud - pass
    the SSH connection to the target host (e.g. LabConnectionKeywords().get_subcloud_ssh(name)).
    """

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to the host where the rule is applied.
        """
        self.ssh_connection = ssh_connection
        self.sudo_password = ConfigurationManager.get_lab_config().get_admin_credentials().get_password()

    def _build_rule(self, action: str, chain: str, port: int, protocol: str, ipv6: bool) -> str:
        """Build the full iptables/ip6tables rule specification.

        Args:
            action (str): The rule action flag ("-A" to add, "-D" to delete).
            chain (str): The chain to target (e.g. "INPUT", "OUTPUT").
            port (int): The destination port to block.
            protocol (str): The protocol (e.g. "tcp").
            ipv6 (bool): If True, use ip6tables; otherwise iptables.

        Returns:
            str: The full rule (e.g. "ip6tables -A INPUT -p tcp --dport 16443 -j DROP").
        """
        tool = "ip6tables" if ipv6 else "iptables"
        return f"{tool} {action} {chain} -p {protocol} --dport {port} -j DROP"

    def block_port(self, port: int, chain: str = "INPUT", protocol: str = "tcp", ipv6: bool = True) -> None:
        """Add a DROP rule blocking traffic to a destination port.

        Args:
            port (int): The destination port to block (e.g. 16443 for the K8s API server).
            chain (str): The chain to add the rule to. Defaults to "INPUT".
            protocol (str): The protocol. Defaults to "tcp".
            ipv6 (bool): If True, use ip6tables; otherwise iptables. Defaults to True.
        """
        rule = self._build_rule("-A", chain, port, protocol, ipv6)
        get_logger().log_info(f"Injecting fault: blocking port {port} ({rule})")
        self.ssh_connection.send(f"echo '{self.sudo_password}' | sudo -S {rule}")
        # Fail fast at the injection point: if the insert fails (bad sudo
        # password, wrong chain, etc.) the auto-rollback would never trigger and
        # the test would otherwise wait out its full timeout for nothing.
        self.validate_success_return_code(self.ssh_connection)

    def unblock_port(self, port: int, chain: str = "INPUT", protocol: str = "tcp", ipv6: bool = True) -> None:
        """Remove a previously added DROP rule blocking traffic to a destination port.

        Safe to call even if the rule is not present (errors are suppressed) so it
        can be used unconditionally in a test finalizer.

        Args:
            port (int): The destination port that was blocked.
            chain (str): The chain the rule was added to. Defaults to "INPUT".
            protocol (str): The protocol. Defaults to "tcp".
            ipv6 (bool): If True, use ip6tables; otherwise iptables. Defaults to True.
        """
        rule = self._build_rule("-D", chain, port, protocol, ipv6)
        get_logger().log_info(f"Removing fault-injection rule: unblocking port {port} ({rule})")
        self.ssh_connection.send(f"echo '{self.sudo_password}' | sudo -S {rule} 2>/dev/null")

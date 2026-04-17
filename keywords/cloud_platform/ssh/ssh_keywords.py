from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.prompt_response import PromptResponse
from framework.ssh.ssh_connection import SSHConnection

from keywords.base_keyword import BaseKeyword

import contextlib
import re


class SSHKeywords(BaseKeyword):
    """
    Class for SSH Keywords
    """

    def __init__(
        self,
        ssh_connection: SSHConnection,
        ssh_username: str,
        ssh_password: str,
    ):
        self.ssh_connection = ssh_connection
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password

    def is_tcp_forwading_configured(self) -> bool:
        """Determine if AllowTcpForwarding=yes in the sshd_config file

        Returns:
            bool: True if tcp forwarding is allowed, False otherwise
        """
        command = "sshd -T -C user=$(whoami) 2>/dev/null | grep -i allowtcpforwarding"
        output = self.ssh_connection.send_as_sudo(cmd=command)
        return any("allowtcpforwarding yes" in line.lower() for line in output)

    def is_tcp_forwading_working(self) -> bool:
        """
        Verify if TCP forwarding is working by creating a local port forward

        Returns:
            bool: True if tcp forwarding is enabled, False otherwise
        """
        tcp_forwarding_enabled = False
        get_logger().log_info("Verifying if TCP forwarding is working")
        output = self.ssh_connection.send(
            cmd="python3 -c 'import socket; s=socket.socket(); s.bind((\"\",0)); print(s.getsockname()[1]); s.close()'"
        )
        port = int(output[0].encode('utf-8').decode('unicode-escape').strip())
        get_logger().log_info(f"Available port: {port}")

        try:
            options = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
            self.ssh_connection.send_expect_prompts(
                cmd=f"ssh -fN {options} -L {port}:localhost:22 {self.ssh_username}@localhost",
                prompts=[
                    PromptResponse("assword", self.ssh_password),
                    PromptResponse("@")
                ]
            )
            if self.ssh_connection.get_return_code() != 0:
                return False

            output = self.ssh_connection.send(cmd=f"nc -zv localhost {port}")
            if "succeeded" in "".join(output).lower():
                self.ssh_connection.send(cmd=f"ssh-keyscan -p {port} localhost")
                tcp_forwarding_enabled = self.ssh_connection.get_return_code() == 0

            get_logger().log_info(f"TCP forwarding is working: {tcp_forwarding_enabled}")

        finally:
            # clean up the background tunnel
            self.ssh_connection.send_as_sudo(
                cmd=f"kill $(lsof -t -i:{port} -sTCP:LISTEN) 2>/dev/null"
            )
        return tcp_forwarding_enabled

    def _configure_tcp_forwarding(self, allow_tcp_forwarding: bool):
        """Configure AllowTcpForwarding in the sshd_config file

        Args:
            allow_tcp_forwarding (bool): Whether to allow or disable tcp
                                         forwarding.

        """
        if self.is_tcp_forwading_configured() == allow_tcp_forwarding:
            # Nothing to do, its already set correctly
            return

        CONFIG_FILE = '/etc/ssh/sshd_config'
        if allow_tcp_forwarding:
            before, after  = 'AllowTcpForwarding no', 'AllowTcpForwarding yes'
        else:
            before, after = 'AllowTcpForwarding yes', 'AllowTcpForwarding no'

        sed_command = f"sed -i 's/{before}/{after}/' {CONFIG_FILE}"
        self.ssh_connection.send_as_sudo(cmd=sed_command)
        if self.ssh_connection.get_return_code() != 0:
            raise KeywordException(f"Failed to modify '{CONFIG_FILE}'")

        # Tell ssh to reload the config file
        self.ssh_connection.send_as_sudo(cmd="systemctl reload ssh")
        if self.ssh_connection.get_return_code() != 0:
            raise KeywordException("Failed to Reload SSH Daemon")

    @contextlib.contextmanager
    def tcp_forwarding_allowed(self):
        """Enable TCP forwarding
        """
        try:
            get_logger().log_info("Enabling TCP forwarding")
            self._configure_tcp_forwarding(allow_tcp_forwarding=True)
            yield True
        finally:
            get_logger().log_info("Disabling TCP forwarding")
            self._configure_tcp_forwarding(allow_tcp_forwarding=False)

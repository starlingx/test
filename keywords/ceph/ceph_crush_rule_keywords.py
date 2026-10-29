"""Keywords for inspecting and changing the CRUSH rule (failure domain) of a Ceph pool."""

import json
from typing import Any

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.ceph.object.ceph_crush_rule_output import CephCrushRuleOutput


class CephCrushRuleKeywords(BaseKeyword):
    """Keywords to read a pool's CRUSH rule and to switch a pool to another rule."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Constructor.

        Args:
            ssh_connection (SSHConnection): SSH connection to a host with Ceph CLI access.
        """
        self.ssh_connection = ssh_connection

    def _send_json(self, command: str) -> Any:
        """Run a Ceph command that prints JSON and parse its output.

        Args:
            command (str): The Ceph command, already including '-f json'.

        Returns:
            Any: The parsed JSON document.

        Raises:
            KeywordException: If the output is not valid JSON.
        """
        output = self.ssh_connection.send(command)
        self.validate_success_return_code(self.ssh_connection)
        text = "\n".join(output) if isinstance(output, list) else str(output)
        try:
            return json.loads(text)
        except json.JSONDecodeError as decode_error:
            raise KeywordException(f"Could not parse JSON output of '{command}': {decode_error}. Raw output: {text}")

    def get_pool_crush_rule_name(self, pool_name: str) -> str:
        """Get the name of the CRUSH rule a pool is using.

        Args:
            pool_name (str): The pool name.

        Returns:
            str: The CRUSH rule name, e.g. 'kube-rbd_host'.
        """
        return self._send_json(f"ceph osd pool get {pool_name} crush_rule -f json")["crush_rule"]

    def get_crush_rule(self, rule_name: str) -> CephCrushRuleOutput:
        """Get a CRUSH rule definition ('ceph osd crush rule dump').

        Args:
            rule_name (str): The CRUSH rule name.

        Returns:
            CephCrushRuleOutput: The parsed rule, exposing its failure domain, root and device class.
        """
        output = self.ssh_connection.send(f"ceph osd crush rule dump {rule_name} -f json")
        self.validate_success_return_code(self.ssh_connection)
        return CephCrushRuleOutput(output)

    def rule_exists(self, rule_name: str) -> bool:
        """Check whether a CRUSH rule exists.

        Args:
            rule_name (str): The CRUSH rule name.

        Returns:
            bool: True if the rule exists, False otherwise.
        """
        return rule_name in self._send_json("ceph osd crush rule ls -f json")

    def create_replicated_rule(self, rule_name: str, root: str, failure_domain: str, device_class: str = "") -> None:
        """Create a replicated CRUSH rule with the given failure domain.

        Args:
            rule_name (str): The new rule name.
            root (str): The CRUSH root to take, e.g. 'storage-tier'.
            failure_domain (str): The bucket type replicas are spread across, e.g. 'osd' or 'host'.
            device_class (str): Optional device class, e.g. 'ssd'.
        """
        get_logger().log_info(f"Create CRUSH rule '{rule_name}' (root={root}, failure domain={failure_domain}, class={device_class or 'any'}).")
        self.ssh_connection.send(f"ceph osd crush rule create-replicated {rule_name} {root} {failure_domain} {device_class}".strip())
        self.validate_success_return_code(self.ssh_connection)

    def set_pool_crush_rule(self, pool_name: str, rule_name: str) -> None:
        """Make a pool use the given CRUSH rule.

        Args:
            pool_name (str): The pool name.
            rule_name (str): The CRUSH rule name.
        """
        get_logger().log_info(f"Set pool '{pool_name}' to use CRUSH rule '{rule_name}'.")
        self.ssh_connection.send(f"ceph osd pool set {pool_name} crush_rule {rule_name}")
        self.validate_success_return_code(self.ssh_connection)

    def delete_rule(self, rule_name: str) -> None:
        """Delete a CRUSH rule. The rule must not be in use by any pool.

        Args:
            rule_name (str): The CRUSH rule name.
        """
        get_logger().log_info(f"Delete CRUSH rule '{rule_name}'.")
        self.ssh_connection.send(f"ceph osd crush rule rm {rule_name}")
        self.validate_success_return_code(self.ssh_connection)

"""Shared BMC credential resolution for IPMI keywords.

Centralizes how a node's BMC connection details (IP, username, password) are
read from the lab configuration, plus the IP validation, so IPMI keywords
(chassis power, SOL console, etc.) do not each re-derive the same thing.
"""

import ipaddress
from typing import Optional

from config.lab.objects.lab_config import LabConfig
from config.lab.objects.node import Node


class BmcCredentials:
    """BMC connection details resolved for a single node."""

    def __init__(self, bm_ip: str, bm_username: Optional[str], bm_password: str):
        """Hold the resolved BMC IP, username, and password.

        Args:
            bm_ip (str): The BMC IP address of the node.
            bm_username (Optional[str]): The BMC username of the node.
            bm_password (str): The BMC password to use for the node.
        """
        self.bm_ip = bm_ip
        self.bm_username = bm_username
        self.bm_password = bm_password

    def get_bm_ip(self) -> str:
        """Get the BMC IP address.

        Returns:
            str: The BMC IP address.
        """
        return self.bm_ip

    def get_bm_username(self) -> Optional[str]:
        """Get the BMC username.

        Returns:
            Optional[str]: The BMC username.
        """
        return self.bm_username

    def get_bm_password(self) -> str:
        """Get the BMC password.

        Returns:
            str: The BMC password.
        """
        return self.bm_password


def resolve_bmc_credentials(node: Node, password_fallback_config: Optional[LabConfig] = None) -> BmcCredentials:
    """Resolve and validate a node's BMC credentials from lab configuration.

    Reads ``bm_ip`` / ``bm_username`` / ``bm_password`` from the given node. When
    the node has no BMC password of its own and ``password_fallback_config`` is
    provided, the password falls back to that config's ``bm_password`` (used for
    subclouds, where the password is often set at the subcloud level rather than
    per node). The BMC IP is validated: it must be set (not empty and not the
    literal string ``"None"``) and a well-formed IP address.

    Args:
        node (Node): The lab node whose BMC credentials to resolve.
        password_fallback_config (Optional[LabConfig]): Config whose
            ``bm_password`` is used when the node has none (e.g. the subcloud
            LabConfig). When None, only the node's own password is used.

    Returns:
        BmcCredentials: The resolved BMC IP, username, and password.

    Raises:
        ValueError: If the BMC IP is not configured, is the literal "None", or
            is not a valid IP address.
    """
    bm_ip = node.get_bm_ip()
    bm_username = node.get_bm_username()
    bm_password = node.get_bm_password()
    if not bm_password and password_fallback_config is not None:
        bm_password = password_fallback_config.get_bm_password()

    if not bm_ip or bm_ip == "None":
        raise ValueError(f"BMC IP for node '{node.get_name()}' is not configured or is None.")
    try:
        ipaddress.ip_address(bm_ip)
    except ValueError:
        raise ValueError(f"Invalid BMC IP address format for node '{node.get_name()}': {bm_ip}")

    return BmcCredentials(bm_ip, bm_username, bm_password)

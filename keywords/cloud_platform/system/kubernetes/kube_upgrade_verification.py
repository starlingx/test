"""Shared Kubernetes-upgrade version verification helpers.

Reusable helpers for reading and verifying the control-plane (Kubernetes) and etcd
versions around an upgrade abort/rollback. Extracted so that multiple test modules
(e.g. the manual and combined upgrade-abort scenarios) share one implementation instead
of duplicating it.
"""

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from framework.validation.validation import validate_equals
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.system.kubernetes.etcd_keywords import EtcdKeywords
from keywords.cloud_platform.system.kubernetes.kube_host_upgrade_list_keywords import KubeHostUpgradeListKeywords


def get_control_plane_version(ssh_connection: SSHConnection, hostname: str) -> str:
    """Get the current control-plane version for a host.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.
        hostname (str): Hostname to query the control-plane version for.

    Returns:
        str: The control-plane version string (e.g. 'v1.31.9').
    """
    kube_host_upgrade_list_keywords = KubeHostUpgradeListKeywords(ssh_connection)
    return kube_host_upgrade_list_keywords.kube_host_upgrade_list().get_host_upgrade_by_hostname(hostname).get_control_plane_version()


def get_etcd_version(ssh_connection: SSHConnection) -> str:
    """Get the current etcd version.

    Args:
        ssh_connection (SSHConnection): SSH connection to the active controller.

    Returns:
        str: The etcd version string.
    """
    etcd_keywords = EtcdKeywords(ssh_connection)
    return etcd_keywords.get_etcd_version()


def verify_kube_and_etcd_versions_rolled_back(hostname: str, original_control_plane_version: str, original_etcd_version: str) -> None:
    """Verify control-plane (kubernetes) and etcd versions rolled back to their originals.

    Establishes a fresh SSH connection to the active controller (the connection may
    have been reset by the abort/rollback) and validates both versions.

    Args:
        hostname (str): Hostname to query the control-plane version for.
        original_control_plane_version (str): Control-plane version recorded before upgrade.
        original_etcd_version (str): Etcd version recorded before upgrade.
    """
    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()

    get_logger().log_test_case_step("Verify control-plane version rolled back to original")
    rollback_version = get_control_plane_version(ssh_connection, hostname)
    get_logger().log_info(f"Control-plane version after abort: {rollback_version}")
    validate_equals(rollback_version, original_control_plane_version, "Control-plane version rolled back to original")

    get_logger().log_test_case_step("Verify etcd version rolled back to original")
    rollback_etcd_version = get_etcd_version(ssh_connection)
    get_logger().log_info(f"Etcd version after abort: {rollback_etcd_version}")
    validate_equals(rollback_etcd_version, original_etcd_version, "Etcd version rolled back to original")

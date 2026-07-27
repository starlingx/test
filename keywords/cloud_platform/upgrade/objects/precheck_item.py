"""Enum for software deploy precheck item names."""

from enum import Enum


class PrecheckItem(Enum):
    """
    Enum representing all possible check items in the 'software deploy precheck' output.

    Each enum value corresponds to the exact string displayed in the precheck output.
    """

    HOSTS_PROVISIONED = "All hosts are provisioned"
    HOSTS_UNLOCKED = "All hosts are unlocked/enabled"
    HOSTS_CONFIGURATIONS = "All hosts have current configurations"
    CEPH_HEALTHY = "Ceph Storage Healthy"
    NO_ALARMS = "No alarms"
    KUBERNETES_NODES = "All kubernetes nodes are ready"
    KUBERNETES_PODS = "All kubernetes control plane pods are ready"
    KUBERNETES_APPS = "All kubernetes applications are in a valid state"
    HOSTS_PATCH_CURRENT = "All hosts are patch current"
    KUBERNETES_VERSION = "Active kubernetes version"
    ACTIVE_CONTROLLER = "Active controller is controller-0"
    LICENSE = "Installed license is valid"
    UPGRADE_PATH = "Valid upgrade path from release"
    PATCHES_APPLIED = "Required patches are applied"
    DOCKER_FILESYSTEM = "Docker filesystem in controllers satisfies the required size of 40GB"
    LVM_AIO_SX = "(LVM snapshots) System is AIO-SX"
    LVM_DISK_SPACE = "(LVM snapshots) Disk space available"

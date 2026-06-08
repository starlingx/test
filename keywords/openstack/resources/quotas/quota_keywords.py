"""Quota management keywords via OpenStack SDK."""

from typing import Dict

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection


class QuotaKeywords(BaseKeyword):
    """Operations for managing OpenStack quotas via SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize QuotaKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def _get_project_id(self, project_name: str) -> str:
        """Resolve project name to ID.

        Args:
            project_name (str): Project name.

        Returns:
            str: Project ID.

        Raises:
            RuntimeError: If project is not found.
        """
        project = self.openstack_connection.get_identity().find_project(project_name)
        if project is None:
            raise RuntimeError(f"Project '{project_name}' not found")
        return project.id

    def _get_fields_needing_update(self, current_quota: object, fields: list) -> Dict[str, int]:
        """Check which quota fields are not already -1.

        Args:
            current_quota (object): Current quota object from SDK.
            fields (list): List of field names to check.

        Returns:
            Dict[str, int]: Fields that need updating (value will be -1).
        """
        updates = {}
        for field in fields:
            if getattr(current_quota, field, 0) != -1:
                updates[field] = -1
        return updates

    def set_unlimited_compute_quotas(self, project_name: str) -> None:
        """Set unlimited Nova compute quotas for fields not already -1.

        Args:
            project_name (str): Project name.
        """
        project_id = self._get_project_id(project_name)
        compute = self.openstack_connection.get_compute()
        current = compute.get_quota_set(project_id)

        fields = ["cores", "instances", "ram", "server_groups", "server_group_members", "key_pairs", "metadata_items"]
        updates = self._get_fields_needing_update(current, fields)

        if not updates:
            get_logger().log_info(f"Compute quotas already unlimited for '{project_name}'")
            return

        get_logger().log_info(f"Setting compute quotas to unlimited for '{project_name}': {list(updates.keys())}")
        compute.update_quota_set(project_id, **updates)

    def set_unlimited_network_quotas(self, project_name: str) -> None:
        """Set unlimited Neutron network quotas for fields not already -1.

        Args:
            project_name (str): Project name.
        """
        project_id = self._get_project_id(project_name)
        network = self.openstack_connection.get_network()
        current = network.get_quota(project_id)

        fields = ["networks", "subnets", "ports", "routers", "floating_ips", "security_groups", "security_group_rules", "rbac_policies", "subnet_pools"]
        updates = self._get_fields_needing_update(current, fields)

        if not updates:
            get_logger().log_info(f"Network quotas already unlimited for '{project_name}'")
            return

        get_logger().log_info(f"Setting network quotas to unlimited for '{project_name}': {list(updates.keys())}")
        network.update_quota(project_id, **updates)

    def set_unlimited_volume_quotas(self, project_name: str) -> None:
        """Set unlimited Cinder volume quotas for fields not already -1.

        Args:
            project_name (str): Project name.
        """
        project_id = self._get_project_id(project_name)
        storage = self.openstack_connection.get_block_storage()
        current = storage.get_quota_set(project_id)

        fields = ["volumes", "gigabytes", "snapshots", "backups", "backup_gigabytes", "per_volume_gigabytes"]
        updates = self._get_fields_needing_update(current, fields)

        if not updates:
            get_logger().log_info(f"Volume quotas already unlimited for '{project_name}'")
            return

        get_logger().log_info(f"Setting volume quotas to unlimited for '{project_name}': {list(updates.keys())}")
        storage.update_quota_set(project_id, **updates)

    def set_unlimited_quotas(self, project_name: str) -> None:
        """Set unlimited quotas for compute, network, and volume services.

        Checks each service individually and only updates fields not already -1.
        Skips entirely if all quotas are already unlimited.

        Args:
            project_name (str): Project name.
        """
        get_logger().log_info(f"Ensuring unlimited quotas for project '{project_name}'")
        self.set_unlimited_compute_quotas(project_name)
        self.set_unlimited_network_quotas(project_name)
        self.set_unlimited_volume_quotas(project_name)

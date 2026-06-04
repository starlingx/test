"""Volume and snapshot CRUD keywords via OpenStack SDK."""

import time
from typing import Dict, List, Optional

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals_with_retry
from keywords.base_keyword import BaseKeyword
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection


class VolumeKeywords(BaseKeyword):
    """CRUD operations for Cinder volumes and snapshots via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize VolumeKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    # ── Volume CRUD ─────────────────────────────────────────────────

    def create_volume(self, volume_name: str, size: int = 1) -> Dict:
        """Create a volume.

        Args:
            volume_name (str): Volume name.
            size (int): Volume size in GB.

        Returns:
            Dict: Volume details.
        """
        get_logger().log_info(f"Creating volume '{volume_name}' (size={size}GB)")
        volume = self.openstack_connection.get_block_storage().create_volume(name=volume_name, size=size)
        return volume.to_dict()

    def show_volume(self, volume_name_or_id: str) -> Dict:
        """Show volume details.

        Args:
            volume_name_or_id (str): Volume name or ID.

        Returns:
            Dict: Volume details.
        """
        storage = self.openstack_connection.get_block_storage()
        volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
        return storage.get_volume(volume.id).to_dict()

    def list_volumes(self) -> List[Dict]:
        """List all volumes.

        Returns:
            List[Dict]: List of volume dicts.
        """
        return [v.to_dict() for v in self.openstack_connection.get_block_storage().volumes()]

    def update_volume(self, volume_name_or_id: str, new_name: Optional[str] = None) -> Dict:
        """Update a volume's name.

        Args:
            volume_name_or_id (str): Volume name or ID.
            new_name (Optional[str]): New volume name.

        Returns:
            Dict: Updated volume details.
        """
        storage = self.openstack_connection.get_block_storage()
        volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
        attrs = {}
        if new_name:
            attrs["name"] = new_name
        updated = storage.update_volume(volume.id, **attrs)
        return updated.to_dict()

    def delete_volume(self, volume_name_or_id: str) -> None:
        """Delete a volume and wait for removal.

        Args:
            volume_name_or_id (str): Volume name or ID.
        """
        get_logger().log_info(f"Deleting volume '{volume_name_or_id}'")
        storage = self.openstack_connection.get_block_storage()
        volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
        storage.delete_volume(volume.id)
        storage.wait_for_delete(volume)

    def wait_for_volume_status(self, volume_name_or_id: str, expected_status: str, timeout: int = 120, poll_interval: int = 5) -> Dict:
        """Poll until volume reaches expected status.

        Args:
            volume_name_or_id (str): Volume name or ID.
            expected_status (str): Expected status string (e.g. 'available').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            Dict: Volume details once status is reached.

        Raises:
            TimeoutError: If status is not reached within timeout.
            RuntimeError: If volume enters error state.
        """
        storage = self.openstack_connection.get_block_storage()
        end_time = time.time() + timeout
        while time.time() < end_time:
            volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
            volume = storage.get_volume(volume.id)
            current_status = volume.status.lower()
            if current_status == expected_status.lower():
                get_logger().log_info(f"Volume '{volume_name_or_id}' reached status '{expected_status}'")
                return volume.to_dict()
            if current_status == "error":
                raise RuntimeError(f"Volume '{volume_name_or_id}' entered error state")
            get_logger().log_info(f"Volume '{volume_name_or_id}' status is '{volume.status}', waiting for '{expected_status}'...")
            time.sleep(poll_interval)
        raise TimeoutError(f"Volume '{volume_name_or_id}' did not reach '{expected_status}' within {timeout}s")

    # ── Volume attach/detach ────────────────────────────────────────

    def attach_volume(self, server_name_or_id: str, volume_name_or_id: str) -> None:
        """Attach a volume to a server.

        Args:
            server_name_or_id (str): Server name or ID.
            volume_name_or_id (str): Volume name or ID.
        """
        get_logger().log_info(f"Attaching volume '{volume_name_or_id}' to server '{server_name_or_id}'")
        compute = self.openstack_connection.get_compute()
        storage = self.openstack_connection.get_block_storage()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
        compute.create_volume_attachment(server.id, volume_id=volume.id)

    def detach_volume(self, server_name_or_id: str, volume_name_or_id: str) -> None:
        """Detach a volume from a server.

        Args:
            server_name_or_id (str): Server name or ID.
            volume_name_or_id (str): Volume name or ID.
        """
        get_logger().log_info(f"Detaching volume '{volume_name_or_id}' from server '{server_name_or_id}'")
        compute = self.openstack_connection.get_compute()
        storage = self.openstack_connection.get_block_storage()
        server = compute.find_server(server_name_or_id, ignore_missing=False)
        volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
        attachments = list(compute.volume_attachments(server.id))
        for attachment in attachments:
            if attachment.volume_id == volume.id:
                compute.delete_volume_attachment(attachment.id, server.id)
                return

    # ── Snapshot CRUD ───────────────────────────────────────────────

    def create_snapshot(self, volume_name_or_id: str, snapshot_name: str) -> Dict:
        """Create a volume snapshot.

        Args:
            volume_name_or_id (str): Source volume name or ID.
            snapshot_name (str): Snapshot name.

        Returns:
            Dict: Snapshot details.
        """
        get_logger().log_info(f"Creating snapshot '{snapshot_name}' from volume '{volume_name_or_id}'")
        storage = self.openstack_connection.get_block_storage()
        volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
        snapshot = storage.create_snapshot(volume_id=volume.id, name=snapshot_name)
        return snapshot.to_dict()

    def show_snapshot(self, snapshot_name_or_id: str) -> Dict:
        """Show snapshot details.

        Args:
            snapshot_name_or_id (str): Snapshot name or ID.

        Returns:
            Dict: Snapshot details.
        """
        storage = self.openstack_connection.get_block_storage()
        snapshot = storage.find_snapshot(snapshot_name_or_id, ignore_missing=False)
        return storage.get_snapshot(snapshot.id).to_dict()

    def list_snapshots(self) -> List[Dict]:
        """List all volume snapshots.

        Returns:
            List[Dict]: List of snapshot dicts.
        """
        return [s.to_dict() for s in self.openstack_connection.get_block_storage().snapshots()]

    def delete_snapshot(self, snapshot_name_or_id: str) -> None:
        """Delete a volume snapshot and wait for removal.

        Args:
            snapshot_name_or_id (str): Snapshot name or ID.
        """
        get_logger().log_info(f"Deleting snapshot '{snapshot_name_or_id}'")
        storage = self.openstack_connection.get_block_storage()
        snapshot = storage.find_snapshot(snapshot_name_or_id, ignore_missing=False)
        storage.delete_snapshot(snapshot.id)
        storage.wait_for_delete(snapshot)

    def wait_for_snapshot_status(self, snapshot_name_or_id: str, expected_status: str, timeout: int = 120, poll_interval: int = 5) -> Dict:
        """Poll until snapshot reaches expected status.

        Args:
            snapshot_name_or_id (str): Snapshot name or ID.
            expected_status (str): Expected status string (e.g. 'available').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            Dict: Snapshot details once status is reached.

        Raises:
            TimeoutError: If status is not reached within timeout.
            RuntimeError: If snapshot enters error state.
        """
        storage = self.openstack_connection.get_block_storage()
        end_time = time.time() + timeout
        while time.time() < end_time:
            snapshot = storage.find_snapshot(snapshot_name_or_id, ignore_missing=False)
            snapshot = storage.get_snapshot(snapshot.id)
            current_status = snapshot.status.lower()
            if current_status == expected_status.lower():
                get_logger().log_info(f"Snapshot '{snapshot_name_or_id}' reached status '{expected_status}'")
                return snapshot.to_dict()
            if current_status == "error":
                raise RuntimeError(f"Snapshot '{snapshot_name_or_id}' entered error state")
            get_logger().log_info(f"Snapshot '{snapshot_name_or_id}' status is '{snapshot.status}', waiting for '{expected_status}'...")
            time.sleep(poll_interval)
        raise TimeoutError(f"Snapshot '{snapshot_name_or_id}' did not reach '{expected_status}' within {timeout}s")

    def is_volume_gone(self, volume_name_or_id: str) -> bool:
        """Check if a volume no longer exists.

        Args:
            volume_name_or_id (str): Volume name or ID.

        Returns:
            bool: True if volume is not found.
        """
        return self.openstack_connection.get_block_storage().find_volume(volume_name_or_id) is None

    # ── Backup operations (generic SDK) ──────────────────────────────

    def delete_backup(self, backup_name_or_id: str) -> None:
        """Delete a volume backup.

        Args:
            backup_name_or_id (str): Backup name or ID.
        """
        get_logger().log_info(f"Deleting backup '{backup_name_or_id}'")
        storage = self.openstack_connection.get_block_storage()
        backup = storage.find_backup(backup_name_or_id, ignore_missing=False)
        storage.delete_backup(backup.id)

    def restore_backup(self, backup_name_or_id: str, volume_name_or_id: Optional[str] = None) -> Dict:
        """Restore a volume backup.

        Args:
            backup_name_or_id (str): Backup name or ID to restore.
            volume_name_or_id (Optional[str]): Target volume to restore into.
                If None, creates a new volume.

        Returns:
            Dict: Restore result with volume_id.
        """
        get_logger().log_info(f"Restoring backup '{backup_name_or_id}'")
        storage = self.openstack_connection.get_block_storage()
        backup = storage.find_backup(backup_name_or_id, ignore_missing=False)
        kwargs = {}
        if volume_name_or_id:
            volume = storage.find_volume(volume_name_or_id, ignore_missing=False)
            kwargs["volume_id"] = volume.id
        result = storage.restore_backup(backup.id, **kwargs)
        return result

    def wait_for_backup_status(
        self,
        backup_name_or_id: str,
        expected_status: str,
        timeout: int = 300,
        poll_interval: int = 10,
    ) -> Dict:
        """Poll until backup reaches expected status.

        Uses validate_equals_with_retry with fail-fast on error state.

        Args:
            backup_name_or_id (str): Backup name or ID.
            expected_status (str): Expected status (e.g. 'available').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            Dict: Backup details once status is reached.

        Raises:
            TimeoutError: If status is not reached within timeout.
            ValidationFailureError: If backup enters error state.
        """
        storage = self.openstack_connection.get_block_storage()

        def get_backup_status() -> str:
            backup = storage.find_backup(backup_name_or_id, ignore_missing=False)
            backup = storage.get_backup(backup.id)
            return backup.status.lower()

        validate_equals_with_retry(
            function_to_execute=get_backup_status,
            expected_value=expected_status.lower(),
            validation_description=f"Backup '{backup_name_or_id}' status == '{expected_status}'",
            timeout=timeout,
            polling_sleep_time=poll_interval,
            failure_values=["error"],
        )

        backup = storage.find_backup(backup_name_or_id, ignore_missing=False)
        backup = storage.get_backup(backup.id)
        get_logger().log_info(f"Backup '{backup_name_or_id}' reached status '{expected_status}'")
        return backup.to_dict()

    # ── Cleanup helpers (safe for teardown — never raise) ────────────

    def cleanup_volume(self, volume_name_or_id: str, server_name: str = None) -> None:
        """Safely delete a volume if it exists. Detaches first if in-use.

        Args:
            volume_name_or_id (str): Volume name or ID.
            server_name (str): Optional server name to detach from if volume is in-use.
        """
        storage = self.openstack_connection.get_block_storage()
        volume = storage.find_volume(volume_name_or_id, ignore_missing=True)
        if volume is None:
            get_logger().log_info(f"Volume '{volume_name_or_id}' already gone, skipping cleanup")
            return
        try:
            if volume.status == "in-use" and server_name:
                self.detach_volume(server_name, volume_name_or_id)
                self.wait_for_volume_status(volume_name_or_id, "available")
            storage.delete_volume(volume.id)
            storage.wait_for_delete(volume)
            get_logger().log_info(f"Cleaned up volume: {volume_name_or_id}")
        except Exception as e:
            get_logger().log_warning(f"Volume cleanup failed for '{volume_name_or_id}': {e}")

    def cleanup_backup(self, backup_name_or_id: str) -> None:
        """Safely delete a backup if it exists. Does not raise on failure.

        Args:
            backup_name_or_id (str): Backup name or ID.
        """
        storage = self.openstack_connection.get_block_storage()
        backup = storage.find_backup(backup_name_or_id, ignore_missing=True)
        if backup is None:
            get_logger().log_info(f"Backup '{backup_name_or_id}' already gone, skipping cleanup")
            return
        try:
            storage.delete_backup(backup.id)
            get_logger().log_info(f"Cleaned up backup: {backup_name_or_id}")
        except Exception as e:
            get_logger().log_warning(f"Backup cleanup failed for '{backup_name_or_id}': {e}")

"""Volume service keywords via OpenStack SDK."""

from typing import List

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals, validate_not_equals
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.services.object.volume_service_list_output import VolumeServiceListOutput


class VolumeServiceKeywords(BaseKeyword):
    """Query operations for Cinder volume services via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize VolumeServiceKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_volume_services(self) -> VolumeServiceListOutput:
        """List all Cinder volume services.

        Returns:
            VolumeServiceListOutput: Parsed service collection.
        """
        raw_services = [s.to_dict() for s in self.openstack_connection.get_block_storage().services()]
        return VolumeServiceListOutput(raw_services)

    def validate_volume_services(self, targets: List[str]) -> None:
        """Validate that targeted volume backend services are up.

        Lists all Cinder volume services, filters to the specified backend
        targets, logs the full service table, and asserts that each matched
        backend has state 'up'.

        Args:
            targets (List[str]): Backend names to check
                (e.g., ``["ceph-rook-store"]`` or ``["netapp-nfs", "netapp-iscsi"]``).

        Raises:
            AssertionError: If any targeted backend service is not 'up'.
        """
        service_output = self.list_volume_services()
        service_output.log_full_service_table()
        targeted_services = service_output.get_targeted_volume_services(targets)
        get_logger().log_info(f"Targeted backends: {targets}")
        validate_not_equals(targeted_services, [], f"Volume services found for targets {targets}")
        for svc in targeted_services:
            backend = svc.get_host().split("@")[1]
            get_logger().log_info(
                f"  {svc.get_binary()} | {svc.get_host()} | {svc.get_status()} | {svc.get_state()}"
            )
            validate_equals(svc.get_state(), "up", f"Backend '{backend}' service state")

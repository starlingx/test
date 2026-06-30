"""Compute service keywords via OpenStack SDK."""

from typing import List

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.base_keyword import BaseKeyword

from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.services.object.compute_service_list_output import ComputeServiceListOutput


class ComputeServiceKeywords(BaseKeyword):
    """Query and validation operations for Nova compute services via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize ComputeServiceKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def list_compute_services(self) -> ComputeServiceListOutput:
        """List all Nova compute services.

        Returns:
            ComputeServiceListOutput: Parsed service collection.
        """
        raw_services = [s.to_dict() for s in self.openstack_connection.get_compute().services()]
        return ComputeServiceListOutput(raw_services)

    def validate_compute_services_up(self, hosts: List[str] = None) -> None:
        """Validate that nova-compute services are up.

        If hosts is provided, validates only those hosts. Otherwise validates
        all nova-compute services are up.

        Args:
            hosts (List[str]): Optional list of hostnames to check.
                If None, validates all nova-compute services.

        Raises:
            AssertionError: If any targeted nova-compute service is not up.
        """
        service_output = self.list_compute_services()
        service_output.log_service_table()
        compute_services = service_output.get_compute_services()

        if hosts:
            compute_services = [s for s in compute_services if s.get_host() in hosts]

        for svc in compute_services:
            get_logger().log_info(
                f"  {svc.get_binary()} | {svc.get_host()} | {svc.get_status()} | {svc.get_state()}"
            )
            validate_equals(svc.get_state(), "up", f"nova-compute on '{svc.get_host()}' state")

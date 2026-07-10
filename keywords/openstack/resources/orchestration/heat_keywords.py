"""Heat stack CRUD keywords via OpenStack SDK orchestration service."""

import time
from typing import Dict, Optional

from framework.logging.automation_logger import get_logger
from keywords.base_keyword import BaseKeyword
from keywords.openstack.connection.ace_openstack_connection import ACEOpenStackConnection
from keywords.openstack.resources.orchestration.object.heat_stack_event_output import HeatStackEventOutput
from keywords.openstack.resources.orchestration.object.heat_stack_output import HeatStackOutput
from keywords.openstack.resources.orchestration.object.heat_stack_resource_output import HeatStackResourceOutput


class HeatKeywords(BaseKeyword):
    """CRUD operations for Heat stacks via OpenStack SDK."""

    def __init__(self, openstack_connection: ACEOpenStackConnection):
        """Initialize HeatKeywords.

        Args:
            openstack_connection (ACEOpenStackConnection): ACE OpenStack connection wrapper.
        """
        self.openstack_connection = openstack_connection

    def create_stack(
        self,
        name: str,
        template: str,
        parameters: Optional[Dict[str, str]] = None,
        timeout: int = 300,
    ) -> HeatStackOutput:
        """Create a Heat stack and wait for CREATE_COMPLETE.

        Args:
            name (str): Stack name.
            template (str): HOT template as a YAML string.
            parameters (Optional[Dict[str, str]]): Template parameters.
            timeout (int): Timeout in seconds to wait for CREATE_COMPLETE.

        Returns:
            HeatStackOutput: Created stack details.

        Raises:
            RuntimeError: If stack enters CREATE_FAILED state.
            TimeoutError: If stack does not reach CREATE_COMPLETE within timeout.
        """
        get_logger().log_info(f"Creating stack '{name}'")
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.create_stack(
            name=name,
            template=template,
            parameters=parameters or {},
        )
        output = self.wait_for_stack_status(stack.id, "CREATE_COMPLETE", timeout=timeout)
        return output

    def delete_stack(self, name_or_id: str, timeout: int = 300, poll_interval: int = 5) -> None:
        """Delete a Heat stack and wait until gone.

        Args:
            name_or_id (str): Stack name or ID.
            timeout (int): Timeout in seconds to wait for deletion.
            poll_interval (int): Seconds between polls.

        Raises:
            TimeoutError: If stack is not deleted within timeout.
        """
        get_logger().log_info(f"Deleting stack '{name_or_id}'")
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=False)
        stack_id = stack.id
        orchestration.delete_stack(stack_id)
        end_time = time.time() + timeout
        while time.time() < end_time:
            found = orchestration.find_stack(stack_id, ignore_missing=True)
            if found is None:
                get_logger().log_info(f"Stack '{name_or_id}' deleted")
                return
            status = found.status.upper() if found.status else ""
            if "FAILED" in status:
                raise RuntimeError(f"Stack '{name_or_id}' deletion failed: {found.status_reason}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Stack '{name_or_id}' not deleted within {timeout}s")

    def update_stack(
        self,
        name_or_id: str,
        template: str,
        parameters: Optional[Dict[str, str]] = None,
        timeout: int = 300,
    ) -> HeatStackOutput:
        """Update a Heat stack and wait for UPDATE_COMPLETE.

        Args:
            name_or_id (str): Stack name or ID.
            template (str): Updated HOT template as a YAML string.
            parameters (Optional[Dict[str, str]]): Updated template parameters.
            timeout (int): Timeout in seconds to wait for UPDATE_COMPLETE.

        Returns:
            HeatStackOutput: Updated stack details.

        Raises:
            RuntimeError: If stack enters UPDATE_FAILED state.
            TimeoutError: If stack does not reach UPDATE_COMPLETE within timeout.
        """
        get_logger().log_info(f"Updating stack '{name_or_id}'")
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=False)
        orchestration.update_stack(
            stack.id,
            template=template,
            parameters=parameters or {},
        )
        output = self.wait_for_stack_status(stack.id, "UPDATE_COMPLETE", timeout=timeout)
        return output

    def get_stack(self, name_or_id: str) -> HeatStackOutput:
        """Get stack details.

        Args:
            name_or_id (str): Stack name or ID.

        Returns:
            HeatStackOutput: Stack details.
        """
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=False)
        return HeatStackOutput([orchestration.get_stack(stack.id).to_dict()])

    def list_stacks(self) -> HeatStackOutput:
        """List all stacks.

        Returns:
            HeatStackOutput: All stacks.
        """
        orchestration = self.openstack_connection.get_orchestration()
        return HeatStackOutput([s.to_dict() for s in orchestration.stacks()])

    def wait_for_stack_status(
        self,
        name_or_id: str,
        expected_status: str,
        timeout: int = 300,
        poll_interval: int = 10,
    ) -> HeatStackOutput:
        """Poll until stack reaches expected status. Fail-fast on *_FAILED.

        Args:
            name_or_id (str): Stack name or ID.
            expected_status (str): Expected status (e.g. 'CREATE_COMPLETE').
            timeout (int): Maximum wait time in seconds.
            poll_interval (int): Seconds between polls.

        Returns:
            HeatStackOutput: Stack details once status is reached.

        Raises:
            RuntimeError: If stack enters a *_FAILED state.
            TimeoutError: If status is not reached within timeout.
        """
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=False)
        stack_id = stack.id
        end_time = time.time() + timeout
        while time.time() < end_time:
            stack_detail = orchestration.get_stack(stack_id)
            current_status = stack_detail.status.upper() if stack_detail.status else ""
            if current_status == expected_status.upper():
                get_logger().log_info(f"Stack '{name_or_id}' reached '{expected_status}'")
                return HeatStackOutput([stack_detail.to_dict()])
            if "FAILED" in current_status:
                raise RuntimeError(f"Stack '{name_or_id}' entered '{current_status}': {stack_detail.status_reason}")
            get_logger().log_info(f"Stack '{name_or_id}' status is '{current_status}', waiting for '{expected_status}'")
            time.sleep(poll_interval)
        raise TimeoutError(f"Stack '{name_or_id}' did not reach '{expected_status}' within {timeout}s")

    def get_stack_resources(self, name_or_id: str) -> HeatStackResourceOutput:
        """List resources created by a stack.

        Args:
            name_or_id (str): Stack name or ID.

        Returns:
            HeatStackResourceOutput: Parsed stack resources.
        """
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=False)
        return HeatStackResourceOutput([r.to_dict() for r in orchestration.resources(stack.id)])

    def get_stack_events(self, name_or_id: str) -> HeatStackEventOutput:
        """Get stack event log.

        Args:
            name_or_id (str): Stack name or ID.

        Returns:
            HeatStackEventOutput: Parsed stack events.
        """
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=False)
        return HeatStackEventOutput([e.to_dict() for e in orchestration.stack_events(stack.id)])

    def verify_stack_resource_exists(
        self,
        name_or_id: str,
        resource_type: str,
        resource_name: Optional[str] = None,
    ) -> bool:
        """Verify a specific resource type exists in the stack.

        Args:
            name_or_id (str): Stack name or ID.
            resource_type (str): OpenStack resource type (e.g. 'OS::Cinder::Volume').
            resource_name (Optional[str]): Logical resource name to match.

        Returns:
            bool: True if resource exists in the stack.
        """
        resources_output = self.get_stack_resources(name_or_id)
        return resources_output.has_resource_type(resource_type, resource_name)

    def cleanup_stack(self, name_or_id: str, timeout: int = 300, poll_interval: int = 5) -> None:
        """Safely delete a stack if it exists. Does not raise on failure.

        Args:
            name_or_id (str): Stack name or ID.
            timeout (int): Timeout in seconds.
            poll_interval (int): Seconds between polls.
        """
        orchestration = self.openstack_connection.get_orchestration()
        stack = orchestration.find_stack(name_or_id, ignore_missing=True)
        if stack is None:
            get_logger().log_info(f"Stack '{name_or_id}' already gone, skipping cleanup")
            return
        stack_id = stack.id
        orchestration.delete_stack(stack_id)
        end_time = time.time() + timeout
        while time.time() < end_time:
            found = orchestration.find_stack(stack_id, ignore_missing=True)
            if found is None:
                get_logger().log_info(f"Stack '{name_or_id}' cleaned up")
                return
            status = found.status.upper() if found.status else ""
            if "FAILED" in status:
                get_logger().log_warning(f"Stack cleanup failed for '{name_or_id}': {found.status_reason}")
                return
            time.sleep(poll_interval)
        get_logger().log_warning(f"Stack cleanup timed out for '{name_or_id}' after {timeout}s")

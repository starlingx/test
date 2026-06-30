"""Keywords for fm event-list command."""

import time
from typing import Optional

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.command_wrappers import source_openrc
from keywords.cloud_platform.fault_management.events.objects.event_list_object import EventListObject
from keywords.cloud_platform.fault_management.events.objects.event_list_output import EventListOutput


class EventListKeywords(BaseKeyword):
    """Keywords for the fm event-list command."""

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize EventListKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the controller.
        """
        self.ssh_connection = ssh_connection

    def get_event_list(self, limit: Optional[int] = None) -> EventListOutput:
        """Get events from fm event-list.

        Args:
            limit (Optional[int]): Maximum number of events to retrieve. If None, retrieves all events.

        Returns:
            EventListOutput: Parsed event list output object.
        """
        cmd = "fm event-list --nowrap"
        if limit is not None:
            cmd += f" -l {limit}"
        output = self.ssh_connection.send(source_openrc(cmd))
        self.validate_success_return_code(self.ssh_connection)
        return EventListOutput(output)

    def wait_for_event(
        self,
        event_log_id: str,
        entity_instance_id: str,
        state: str,
        start_time: Optional[str] = None,
        timeout: int = 120,
        check_interval: int = 5,
    ) -> EventListObject:
        """Wait for an event with the specified attributes to appear.

        Args:
            event_log_id (str): Event log ID to match (e.g. '200.001').
            entity_instance_id (str): Entity instance ID to match (e.g. 'host=compute-0').
            state (str): Expected state ('set' or 'clear').
            start_time (Optional[str]): Only match events with timestamps after this value.
            timeout (int): Maximum seconds to wait. Defaults to 120.
            check_interval (int): Seconds between polls. Defaults to 5.

        Raises:
            TimeoutError: If the event is not found within the timeout period.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            event_output = self.get_event_list(limit=20)
            for event in event_output.get_events():
                if (
                    event.get_event_log_id() == event_log_id
                    and entity_instance_id in event.get_entity_instance_id()
                    and event.get_state() == state
                ):
                    if start_time and event.get_time_stamp() < start_time:
                        continue
                    get_logger().log_info(
                        f"Event found: event_log_id={event_log_id}, "
                        f"entity={entity_instance_id}, state={state}"
                    )
                    return event
            get_logger().log_info(
                f"Waiting for event: event_log_id={event_log_id}, "
                f"entity={entity_instance_id}, state={state}"
            )
            time.sleep(check_interval)

        raise TimeoutError(
            f"Event not found within {timeout}s: "
            f"event_log_id={event_log_id}, entity={entity_instance_id}, state={state}"
        )

from keywords.cloud_platform.fault_management.events.objects.fm_event_list_object import FmEventListObject
from keywords.cloud_platform.fault_management.fault_management_table_parser import FaultManagementTableParser


class FmEventListOutput:
    """Class for parsing 'fm event-list' command output."""

    def __init__(self, event_list_output: list) -> None:
        """
        Constructor.

        Args:
            event_list_output (list): Raw output from 'fm event-list' command.
        """
        self.events: list[FmEventListObject] = []
        fault_management_table_parser = FaultManagementTableParser(event_list_output)
        output_values = fault_management_table_parser.get_output_values_list()

        for value in output_values:
            event_object = FmEventListObject()
            if "UUID" in value:
                event_object.set_uuid(value["UUID"])
            if "Time Stamp" in value:
                event_object.set_time_stamp(value["Time Stamp"])
            if "State" in value:
                event_object.set_state(value["State"])
            if "Event Log ID" in value:
                event_object.set_event_log_id(value["Event Log ID"])
            if "Reason Text" in value:
                event_object.set_reason_text(value["Reason Text"])
            if "Entity Instance ID" in value:
                event_object.set_entity_instance_id(value["Entity Instance ID"])
            if "Severity" in value:
                event_object.set_severity(value["Severity"])
            self.events.append(event_object)

    def get_events(self) -> list[FmEventListObject]:
        """
        Get the list of event objects.

        Returns:
            list[FmEventListObject]: List of event objects.
        """
        return self.events

    def get_event_log_ids(self) -> list[str]:
        """
        Get all event log IDs.

        Returns:
            list[str]: List of event log IDs.
        """
        return [event.get_event_log_id() for event in self.events]

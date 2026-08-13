"""Output class for FM Event Log REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.fm.objects.fm_event_log_object import FmEventLogObject


class FmEventLogOutput:
    """Parses FM /event_log REST API response into FmEventLogObject list."""

    def __init__(self, response: RestResponse):
        """Initialize FmEventLogOutput from REST response.

        Args:
            response (RestResponse): The REST response from FM /event_log API.
        """
        self.event_log_objects = []
        event_logs = response.get_json_content().get("event_log", [])
        for event in event_logs:
            event_object = FmEventLogObject()
            if event.get("event_log_id"):
                event_object.set_event_log_id(event["event_log_id"])
            if event.get("reason_text"):
                event_object.set_reason_text(event["reason_text"])
            if event.get("entity_instance_id"):
                event_object.set_entity_instance_id(event["entity_instance_id"])
            if event.get("severity"):
                event_object.set_severity(event["severity"])
            if event.get("timestamp"):
                event_object.set_timestamp(event["timestamp"])
            if event.get("state"):
                event_object.set_state(event["state"])
            self.event_log_objects.append(event_object)

    def get_event_log_objects(self) -> list[FmEventLogObject]:
        """Get list of FmEventLogObject.

        Returns:
            list[FmEventLogObject]: List of FmEventLogObject instances.
        """
        return self.event_log_objects

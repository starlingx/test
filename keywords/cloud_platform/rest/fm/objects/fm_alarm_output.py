"""Output class for FM Alarm REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.fault_management.alarms.objects.alarm_list_object import AlarmListObject


class FmAlarmOutput:
    """Parses FM /alarms REST API response into AlarmListObject list."""

    def __init__(self, response: RestResponse):
        """Initialize FmAlarmOutput from REST response.

        Args:
            response (RestResponse): The REST response from FM /alarms API.
        """
        self.alarm_objects = []
        alarms = response.get_json_content().get("alarms", [])
        for alarm in alarms:
            alarm_object = AlarmListObject()
            if alarm.get("uuid"):
                alarm_object.set_uuid(alarm["uuid"])
            if alarm.get("alarm_id"):
                alarm_object.set_alarm_id(alarm["alarm_id"])
            if alarm.get("reason_text"):
                alarm_object.set_reason_text(alarm["reason_text"])
            if alarm.get("entity_instance_id"):
                alarm_object.set_entity_id(alarm["entity_instance_id"])
            if alarm.get("severity"):
                alarm_object.set_severity(alarm["severity"])
            if alarm.get("timestamp"):
                alarm_object.set_time_stamp(alarm["timestamp"])
            self.alarm_objects.append(alarm_object)

    def get_alarm_objects(self) -> list[AlarmListObject]:
        """Get list of AlarmListObject.

        Returns:
            list[AlarmListObject]: List of AlarmListObject instances.
        """
        return self.alarm_objects

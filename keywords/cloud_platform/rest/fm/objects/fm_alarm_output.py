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
            # The FM alarm model carries a 'mgmt_affecting' flag per alarm; an
            # alarm is management-affecting when it reads True.
            if "mgmt_affecting" in alarm:
                alarm_object.set_mgmt_affecting(self._to_bool(alarm["mgmt_affecting"]))
            self.alarm_objects.append(alarm_object)

    @staticmethod
    def _to_bool(value) -> bool:
        """Coerce the REST 'mgmt_affecting' field to a boolean.

        The field is a boolean flag; accept native booleans and the string
        forms 'true'/'false' (case-insensitive) that some API versions emit.

        Args:
            value: The raw 'mgmt_affecting' value from the alarm payload.

        Returns:
            bool: True when the value represents a management-affecting alarm.
        """
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() == "true"

    def get_alarm_objects(self) -> list[AlarmListObject]:
        """Get list of AlarmListObject.

        Returns:
            list[AlarmListObject]: List of AlarmListObject instances.
        """
        return self.alarm_objects

    def get_mgmt_affecting_alarms(self) -> list[AlarmListObject]:
        """Get only the alarms that are management-affecting.

        Management-affecting alarms are the class that blocks a
        sw-deploy-strategy precheck during an orchestrated patch/upgrade.

        Returns:
            list[AlarmListObject]: Alarms whose management-affecting flag is True.
        """
        return [alarm for alarm in self.alarm_objects if alarm.get_mgmt_affecting()]

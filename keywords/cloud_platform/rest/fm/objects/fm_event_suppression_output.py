"""Output class for FM Event Suppression REST API response."""

from framework.rest.rest_response import RestResponse
from keywords.cloud_platform.rest.fm.objects.fm_event_suppression_object import FmEventSuppressionObject


class FmEventSuppressionOutput:
    """Parses FM /event_suppression REST API response into FmEventSuppressionObject list."""

    def __init__(self, response: RestResponse):
        """Initialize FmEventSuppressionOutput from REST response.

        Args:
            response (RestResponse): The REST response from FM /event_suppression API.
        """
        self.event_suppression_objects = []
        suppressions = response.get_json_content().get("event_suppression", [])
        for suppression in suppressions:
            obj = FmEventSuppressionObject()
            if suppression.get("uuid"):
                obj.set_uuid(suppression["uuid"])
            if suppression.get("alarm_id"):
                obj.set_alarm_id(suppression["alarm_id"])
            if suppression.get("suppression_status"):
                obj.set_suppression_status(suppression["suppression_status"])
            self.event_suppression_objects.append(obj)

    def get_event_suppression_objects(self) -> list[FmEventSuppressionObject]:
        """Get list of FmEventSuppressionObject.

        Returns:
            list[FmEventSuppressionObject]: List of FmEventSuppressionObject instances.
        """
        return self.event_suppression_objects

"""Keywords for FM (Fault Management) REST API operations."""

from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.rest.cloud_rest_client import CloudRestClient
from keywords.cloud_platform.rest.fm.objects.fm_alarm_output import FmAlarmOutput
from keywords.cloud_platform.rest.fm.objects.fm_event_log_output import FmEventLogOutput
from keywords.cloud_platform.rest.fm.objects.fm_event_suppression_output import FmEventSuppressionOutput
from keywords.cloud_platform.rest.fm.objects.fm_v1_output import FmV1Output
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


class GetFmKeywords(BaseKeyword):
    """Keywords for FM REST API GET operations."""

    def __init__(self):
        """Initialize GetFmKeywords with FM base URL."""
        self.fm_base_url = GetRestUrlKeywords().get_fm_url()

    def get_alarms(self) -> FmAlarmOutput:
        """Get alarms from FM REST API.

        Returns:
            FmAlarmOutput: Parsed alarm output with AlarmListObject list.
        """
        response = CloudRestClient().get(f"{self.fm_base_url}/alarms")
        self.validate_success_status_code(response)
        return FmAlarmOutput(response)

    def get_v1(self) -> FmV1Output:
        """Get FM API v1 root.

        Returns:
            FmV1Output: Parsed v1 output with links and version info.
        """
        response = CloudRestClient().get(f"{self.fm_base_url}/v1")
        self.validate_success_status_code(response)
        return FmV1Output(response)

    def get_event_log(self) -> FmEventLogOutput:
        """Get event log from FM REST API.

        Returns:
            FmEventLogOutput: Parsed event log output with FmEventLogObject list.
        """
        response = CloudRestClient().get(f"{self.fm_base_url}/event_log")
        self.validate_success_status_code(response)
        return FmEventLogOutput(response)

    def get_event_suppression(self) -> FmEventSuppressionOutput:
        """Get event suppression from FM REST API.

        Returns:
            FmEventSuppressionOutput: Parsed event suppression output.
        """
        response = CloudRestClient().get(f"{self.fm_base_url}/event_suppression")
        self.validate_success_status_code(response)
        return FmEventSuppressionOutput(response)

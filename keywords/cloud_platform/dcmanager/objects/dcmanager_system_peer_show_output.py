from typing import Dict

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_vertical_table_parser import DcManagerVerticalTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_system_peer_show_object import DcManagerSystemPeerShowObject


class DcManagerSystemPeerShowOutput:
    """Parses the output of the 'dcmanager system-peer show' command into a DcManagerSystemPeerShowObject instance."""

    def __init__(self, dcmanager_output: str):
        """Constructor

        Args:
            dcmanager_output (str): Output of the 'dcmanager system-peer show' command.

        Raises:
            KeywordException: If the output format is invalid.
        """
        dc_vertical_table_parser = DcManagerVerticalTableParser(dcmanager_output)
        output_values = dc_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.dcmanager_system_peer_show = DcManagerSystemPeerShowObject(
                id=output_values.get("id", ""),
                peer_uuid=output_values.get("peer uuid", ""),
                peer_name=output_values.get("peer name", ""),
                manager_endpoint=output_values.get("manager endpoint", ""),
                manager_username=output_values.get("manager username", ""),
                controller_gateway_address=output_values.get("controller gateway address", ""),
                administrative_state=output_values.get("administrative state", ""),
                availability_state=output_values.get("availability state", ""),
                heartbeat_interval=output_values.get("heartbeat interval", ""),
                heartbeat_failure_threshold=output_values.get("heartbeat failure threshold", ""),
                heartbeat_failure_policy=output_values.get("heartbeat failure policy", ""),
                heartbeat_maintenance_timeout=output_values.get("heartbeat maintenance timeout", ""),
            )
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_dcmanager_system_peer_show_object(self) -> DcManagerSystemPeerShowObject:
        """Retrieves the parsed dcmanager system peer show object.

        Returns:
            DcManagerSystemPeerShowObject: The parsed dcmanager system peer show object.
        """
        return self.dcmanager_system_peer_show

    @staticmethod
    def is_valid_output(value: Dict[str, str]) -> bool:
        """Checks if the output contains all the required fields.

        Args:
            value (Dict[str, str]): The dictionary of output values.

        Returns:
            bool: True if all required fields are present, False otherwise.
        """
        required_fields = ["id", "peer uuid", "peer name", "manager endpoint", "manager username", "controller gateway address", "administrative state", "availability state", "heartbeat interval", "heartbeat failure threshold", "heartbeat failure policy", "heartbeat maintenance timeout"]
        missing_fields = set(required_fields) - set(value.keys())

        if missing_fields:
            get_logger().log_error(f"Missing fields in output: {', '.join(missing_fields)}")
            return False
        return True

    def __str__(self) -> str:
        """String representation of the system peer object.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}"

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: String representation.
        """
        return self.__str__()

from typing import List

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.dcmanager.dcmanager_table_parser import DcManagerTableParser
from keywords.cloud_platform.dcmanager.objects.dcmanager_system_peer_list_object import DcManagerSystemPeerListObject


class DcManagerSystemPeerListOutput:
    """This class represents the output of the 'dcmanager system peer list' command."""

    def __init__(self, dcmanager_output: str):
        """Constructor

        Args:
            dcmanager_output (str): The output string from dcmanager system peer list command

        """
        self.dcmanager_sys_peer_list: List[DcManagerSystemPeerListObject] = []
        dc_table_parser = DcManagerTableParser(dcmanager_output)
        output_values = dc_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                self.dcmanager_sys_peer_list.append(DcManagerSystemPeerListObject(id=value.get("id", ""), peer_uuid=value.get("peer uuid", ""), peer_name=value.get("peer name", ""), manager_endpoint=value.get("manager endpoint", ""), controller_gateway_address=value.get("controller gateway address", "")))
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_dcmanager_peer_list(self) -> List[DcManagerSystemPeerListObject]:
        """Get the list of dcmanager system peer objects.

        Returns:
            List[DcManagerSystemPeerListObject]: List of system peer objects

        """
        return self.dcmanager_sys_peer_list

    def is_valid_output(self, value: dict) -> bool:
        """
        Validates that the output dictionary contains all required fields.

        This method checks if all mandatory fields are present in the provided dictionary.
        The dictionary keys can be a superset (contain additional fields beyond required ones).

        Args:
            value (dict): Dictionary containing parsed output values from dcmanager command.
                        Keys represent field names, values represent field data.

        Returns:
            bool: True if all required fields are present in value.keys(), False otherwise.

        Note:
            Logs an error message for missing fields before returning False.
        """
        # Define all mandatory fields that must be present in the output
        required_fields = ["id", "peer name", "peer uuid", "manager endpoint", "controller gateway address"]

        # Check if all required fields are subset of value keys using set operations
        missing_fields = set(required_fields) - set(value.keys())

        if missing_fields:
            # Log all missing fields at once for debugging
            get_logger().log_error(f"Missing fields in output: {', '.join(missing_fields)}")
            return False

        return True

    def __str__(self) -> str:
        """String representation of the system peer object.

        Returns:
            str: String representation.
        """
        return f"{self.__class__.__name__}(rows={len(self.dcmanager_sys_peer_list)})"

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            str: String representation.
        """
        return self.__str__()

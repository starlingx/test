"""Module for parsing and validating software patch query output."""

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.sw_patch.objects.query_object import SwPatchQueryObject
from keywords.cloud_platform.sw_patch.query_parser import SwPatchQueryParser

class SwPatchQueryOutput:
    """Processes and stores software patch query output."""

    def __init__(self, sw_patch_output: str):
        """Initializes SwPatchQueryOutput by parsing the patch query.

        Args:
            sw_patch_output (str): The raw output of the sw-patch query.

        Raises:
            KeywordException: If the output format is invalid.
        """
        self.sw_patches: list[SwPatchQueryObject] = []
        sw_query_parser = SwPatchQueryParser(sw_patch_output)
        output_values = sw_query_parser.to_list_of_dicts()

        for value in output_values:
            if self.is_valid_output(value):
                patch_obj = SwPatchQueryObject(
                    patch_id=value["Patch ID"],
                    reboot_required=value["RR"],
                    release=value["Release"],
                    state=value["Patch State"],
                )
                self.sw_patches.append(patch_obj)
            else:
                raise KeywordException(f"Invalid output line: {value}")

    def get_patches(self) -> list[SwPatchQueryObject]:
        """Returns the list of parsed software patches.

        Returns:
            list[SwPatchQueryObject]: List of software patch objects.
        """
        return self.sw_patches

    def get_last_patch(self) -> SwPatchQueryObject:
        """Returns the last software patch in the list.

        Returns:
            SwPatchQueryObject: The last software patch object.
        """
        if not self.sw_patches:
            raise KeywordException("No patches found in the output.")
        return self.sw_patches[-1]

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """Validates the presence of required keys in the patch output.

        Args:
            value (dict): Dictionary containing patch information.

        Returns:
            bool: True if all required keys are present, otherwise False.
        """
        required_keys = {"Patch ID", "RR", "Release", "Patch State"}
        missing_keys = required_keys - value.keys()

        for key in missing_keys:
            get_logger().log_error(f"{key} is missing in the output value: {value}")

        return not missing_keys

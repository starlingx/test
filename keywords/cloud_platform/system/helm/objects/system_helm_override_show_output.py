from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.helm.objects.system_helm_override_show_object import HelmOverrideShowObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHelmOverrideShowOutput:
    """
    This class parses the output of 'system helm-override-show' command into an object of type HelmOverrideShowObject.
    """

    def __init__(self, helm_override_show_output: str):
        """
        Initialize the SystemHelmOverrideShowOutput class.

        Args:
            helm_override_show_output (str): Output of the 'system helm-override-show' command.

        Raises:
            KeywordException: If the output is not valid.
        """
        system_vertical_table_parser = SystemVerticalTableParser(helm_override_show_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.helm_override_show = HelmOverrideShowObject()
            self.helm_override_show.set_name(output_values["name"])
            self.helm_override_show.set_namespace(output_values["namespace"])
            self.helm_override_show.set_attributes(output_values["attributes"])
            self.helm_override_show.set_combined_overrides(output_values["combined_overrides"])
            self.helm_override_show.set_system_overrides(output_values["system_overrides"])
            self.helm_override_show.set_user_overrides(output_values["user_overrides"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_helm_override_show(self) -> HelmOverrideShowObject:
        """
        Returns the parsed helm override object.

        Returns:
            HelmOverrideShowObject: The parsed helm override object.
        """
        return self.helm_override_show

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        required_fields = ["name", "namespace", "attributes", "combined_overrides", "system_overrides", "user_overrides"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                valid = False
                break
        return valid

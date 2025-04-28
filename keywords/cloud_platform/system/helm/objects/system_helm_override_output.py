from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.helm.objects.system_helm_override_object import HelmOverrideObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHelmOverrideOutput:
    """
    This class parses the output of 'system helm-override-list' command into an object of type HelmOverrideObject.
    """

    def __init__(self, helm_override_output: str):
        """
        Constructor

        Args:
            helm_override_output (str): Output of the 'system helm-override-list' command.

        Raises:
            KeywordException: If the output is not valid.
        """
        system_vertical_table_parser = SystemVerticalTableParser(helm_override_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.helm_override = HelmOverrideObject()
            self.helm_override.set_name(output_values["name"])
            self.helm_override.set_namespace(output_values["namespace"])
            self.helm_override.set_user_overrides(output_values["user_overrides"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_helm_override_list(self) -> HelmOverrideObject:
        """
        Returns the parsed helm override list object.

        Returns:
            HelmOverrideObject: The parsed helm override object list.
        """
        return self.helm_override

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        required_fields = ["name", "namespace", "user_overrides"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                valid = False
                break
        return valid

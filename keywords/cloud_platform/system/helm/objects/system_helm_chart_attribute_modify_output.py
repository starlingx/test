from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.helm.objects.system_helm_chart_attribute_modify_object import HelmChartAttributeModifyObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser
from typing import Dict

class SystemHelmChartAttributeModifyOutput:
    """
    This class parses the output of the 'system helm-chart-attribute-modify' command
    into an object of type HelmChartAttributeModifyObject.
    """

    def __init__(self, helm_chart_attribute_modify_output: str):
        """
        Initialize the SystemHelmChartAttributeModifyOutput class.

        Args:
            helm_chart_attribute_modify_output (str): Output of the 'system helm-chart-attribute-modify' command.

        Raises:
            KeywordException: If the output is not valid.
        """
        system_vertical_table_parser = SystemVerticalTableParser(helm_chart_attribute_modify_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.helm_chart_attribute_modify = HelmChartAttributeModifyObject()
            self.helm_chart_attribute_modify.set_name(output_values["name"])
            self.helm_chart_attribute_modify.set_namespace(output_values["namespace"])
            self.helm_chart_attribute_modify.set_attributes(output_values["attributes"])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_helm_chart_attribute_modify(self) -> 'HelmChartAttributeModifyObject':
        """
        Returns the parsed helm chart attribute modify object.

        Returns:
            HelmChartAttributeModifyObject: The parsed object representing the modified chart attributes.
        """
        return self.helm_chart_attribute_modify

    @staticmethod
    def is_valid_output(value: Dict) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        required_fields = ["attributes", "name", "namespace"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f"{field} is not in the output value")
                valid = False
                break
        return valid

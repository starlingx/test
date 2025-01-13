from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.cluster.objects.system_cluster_object import SystemClusterObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemClusterShowOutput:
    """
    This class parses the output of 'system cluster-show' command into an object of type SystemClusterObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system cluster-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_cluster = SystemClusterObject()
            self.system_cluster.set_uuid(output_values['uuid'])
            self.system_cluster.set_cluster_uuid(output_values['cluster_uuid'])
            self.system_cluster.set_type(output_values['type'])
            self.system_cluster.set_name(output_values['name'])
            self.system_cluster.set_replication_groups(output_values['replication_groups'])
            self.system_cluster.set_storage_tiers(output_values['storage_tiers'])
            self.system_cluster.set_deployment_model(output_values['deployment_model'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_cluster_show(self):
        """
        Returns the parsed system cluster object.

        Returns:
        SystemClusterObject: The parsed system cluster object.
        """

        return self.system_cluster

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "cluster_uuid", "type", "name", "replication_groups", "storage_tiers",
                           "deployment_model"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid

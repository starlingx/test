from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.cluster.objects.system_cluster_object import SystemClusterObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemClusterOutput:
    """
    This class parses the output of 'system cluster-list' command into an object of type SystemClusterObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system cluster-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_cluster : [SystemClusterObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_cluster = SystemClusterObject()
                system_cluster.set_uuid(value['uuid'])
                system_cluster.set_cluster_uuid(value['cluster_uuid'])
                system_cluster.set_type(value['type'])
                system_cluster.set_name(value['name'])
                system_cluster.set_deployment_model(value['deployment_model'])
                self.system_cluster.append(system_cluster)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_cluster_list(self):
        """
        Returns the parsed system cluster_list object.

        Returns:
        SystemClusterMonObject: The parsed system cluster object.
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

        required_fields = ["uuid", "cluster_uuid", "type", "name", "deployment_model"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid

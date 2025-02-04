from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.storage.objects.system_storage_tier_object import SystemStorageTierObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemStorageTierShowOutput:
    """
    This class parses the output of 'system storage-tier-show' command into an object of type SystemStorageTierObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system storage-tier-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_storage_tier = SystemStorageTierObject()
            self.system_storage_tier.set_uuid(output_values['uuid'])
            self.system_storage_tier.set_name(output_values['name'])
            self.system_storage_tier.set_type(output_values['type'])
            self.system_storage_tier.set_status(output_values['status'])
            self.system_storage_tier.set_backend_uuid(output_values['backend_uuid'])
            self.system_storage_tier.set_cluster_uuid(output_values['cluster_uuid'])
            self.system_storage_tier.set_osds(output_values['OSDs'])
            self.system_storage_tier.set_created_at(output_values['created_at'])
            self.system_storage_tier.set_updated_at(output_values['updated_at'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_storage_tier_show(self):
        """
        Returns the parsed system storage-tier-show object.

        Returns:
        SystemStorageTierObject: The parsed system storage-tier-show object.
        """

        return self.system_storage_tier

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "name", "type", "status", "backend_uuid", "cluster_uuid", "OSDs",
                           "created_at", "updated_at"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid

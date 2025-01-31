from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.storage.objects.system_storage_tier_object import SystemStorageTierObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemStorageTierOutput:
    """
    This class parses the output of 'system storage-tier-list' command into an object of type SystemStorageTierObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system storage-tier-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_storage_tier : [SystemStorageTierObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_storage_tier = SystemStorageTierObject()
                system_storage_tier.set_uuid(value['uuid'])
                system_storage_tier.set_name(value['name'])
                system_storage_tier.set_status(value['status'])
                system_storage_tier.set_backend_using(value['backend_using'])
                self.system_storage_tier.append(system_storage_tier)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_storage_tier_list(self):
        """
        Returns the parsed system storage_tier_list object.

        Returns:
        SystemStorageTierObject: The parsed system storage-tier object.
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

        required_fields = ["uuid", "name", "status", "backend_using"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid

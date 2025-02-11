from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.remotelogging.objects.system_remotelogging_object import SystemRemoteloggingObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemRemoteloggingShowOutput:
    """
    This class parses the output of 'system remotelogging-show' command into an object of type SystemRemoteloggingShowObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system remotelogging-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_remotelog = SystemRemoteloggingObject()
            self.system_remotelog.set_uuid(output_values['uuid'])
            self.system_remotelog.set_ip_address(output_values['ip_address'])
            self.system_remotelog.set_enabled(output_values['enabled'])
            self.system_remotelog.set_transport(output_values['transport'])
            self.system_remotelog.set_port(output_values['port'])
            self.system_remotelog.set_created_at(output_values['created_at'])
            self.system_remotelog.set_updated_at(output_values['updated_at'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_remotelogging_show(self) -> SystemRemoteloggingObject:
        """
        Returns the parsed system remotelogging-show object.

        Returns:
        SystemRemoteloggingObject: The parsed system remotelogging-show object.
        """

        return self.system_remotelog

    @staticmethod
    def is_valid_output(value) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "ip_address", "enabled", "transport", "port", "created_at", "updated_at"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid
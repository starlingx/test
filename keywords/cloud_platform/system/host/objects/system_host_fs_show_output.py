from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_fs_object import SystemHostFSObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemHostFSShowOutput:
    """
    Parses the output of the 'system host-fs-show' command into an object of type SystemHostFSObject.
    """

    def __init__(self, system_output: str):
        """
        Initializes the SystemHostFSShowOutput with the command output.

        Args:
            system_output (str): Output of the 'system host-fs-show' command.

        Raises:
            KeywordException: If the output is not valid.
        """
        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_host_fs_show_object = SystemHostFSObject(
                output_values['uuid'],
                output_values['name'],
                int(output_values['size']) if output_values['size'] else 0,
                output_values['logical_volume'],
                output_values['state'],
            )
            if 'created_at' in output_values:
                self.system_host_fs_show_object.set_created_at(output_values['created_at'])
            if 'updated_at' in output_values:
                self.system_host_fs_show_object.set_updated_at(output_values['updated_at'])
            if 'capabilities' in output_values:
                self.system_host_fs_show_object.set_capabilities(output_values['capabilities'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_filesystems(self) -> SystemHostFSObject:
        """
        Returns the parsed host filesystem object.

        Returns:
            SystemHostFSObject: The parsed host filesystem object.
        """
        return self.system_host_fs_show_object

    @staticmethod
    def is_valid_output(value: dict) -> bool:
        """
        Checks if the output contains all the expected fields.

        Args:
            value (dict): The dictionary of output values.

        Returns:
            bool: True if the output contains all required fields, False otherwise.
        """
        valid = True
        required_fields = ['uuid', 'name', 'size', 'logical_volume', 'state', 'created_at', 'updated_at']

        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value: {value}')
                valid = False
        return valid
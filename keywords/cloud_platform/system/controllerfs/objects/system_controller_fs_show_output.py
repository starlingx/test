from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.controllerfs.objects.system_controllerfs_object import SystemControllerFSObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser


class SystemControllerFSShowOutput:
    """
    This class parses the output of 'system controllerfs-show' command into an object of type SystemControllerFSShowObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_controllerfs_show_output: output of 'system controllerfs-show' command.
        """
        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_controllerfs_show_object = SystemControllerFSObject(
                output_values['uuid'],
                output_values['name'],
                int(output_values['size']) if output_values['size'] else 0,
                output_values['logical_volume'],
                output_values['replicated'].lower() == 'true',
                output_values['created_at'],
                output_values['updated_at']
                )
            if 'state' in output_values:
                self.system_controllerfs_show_object.set_state(output_values['state'])
            if 'capabilities' in output_values:
                self.system_controllerfs_show_object.set_capabilities(output_values['capabilities'])
        else:
                raise KeywordException(f"The output line {output_values} was not valid")

    def get_filesystems(self):
        return self.system_controllerfs_show_object

    @staticmethod
    def is_valid_output(value):
        """
        This function is to check if the output contains all the expected fields.
        """

        valid = True
        if 'uuid' not in value:
            get_logger().log_error(f'UUID is not in the output value: {value}')
            valid = False
        if 'name' not in value:
            get_logger().log_error(f'FS Name is not in the output value: {value}')
            valid = False
        if 'size' not in value:
            get_logger().log_error(f'Size is not in the output value: {value}')
            valid = False
        if 'logical_volume' not in value:
            get_logger().log_error(f'Logical Volume is not in the output value: {value}')
            valid = False
        if 'replicated' not in value:
            get_logger().log_error(f'Replicated is not in the output value: {value}')
            valid = False
        if 'created_at' not in value:
            get_logger().log_error(f'created_at is not in the output value: {value}')
            valid = False
        if 'updated_at' not in value:
            get_logger().log_error(f'updated_at is not in the output value: {value}')
            valid = False
        return valid

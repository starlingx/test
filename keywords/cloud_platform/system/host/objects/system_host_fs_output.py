from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_fs_object import SystemHostFSObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostFSOutput:

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_host_fs_output: output of 'system host-fs-list' command.
        """

        self.system_host_fs : [SystemHostFSObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                host_fs = SystemHostFSObject(
                    value['UUID'],
                    value['FS Name'],
                    int(value['Size in GiB']) if value['Size in GiB'] else 0,
                    value['Logical Volume'],
                    value['State'],
                )
                if 'Capabilities' in value:
                    host_fs.set_capabilities(value['Capabilities'])
                self.system_host_fs.append(host_fs)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_filesystems(self):
        """
        This function is to return the list of host filesystems
        """
        return self.system_host_fs

    @staticmethod
    def is_valid_output(value):
        """
        This function is to check if the output contains all the expected fields.
        """

        valid = True
        if 'UUID' not in value:
            get_logger().log_error(f'UUID is not in the output value: {value}')
            valid = False
        if 'FS Name' not in value:
            get_logger().log_error(f'FS Name is not in the output value: {value}')
            valid = False
        if 'Size in GiB' not in value:
            get_logger().log_error(f'Size is not in the output value: {value}')
            valid = False
        if 'Logical Volume' not in value:
            get_logger().log_error(f'Logical Volume is not in the output value: {value}')
            valid = False
        if 'State' not in value:
            get_logger().log_error(f'State is not in the output value: {value}')
            valid = False
        return valid

from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.controllerfs.objects.system_controllerfs_object import SystemControllerFSObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemControllerFSOutput:
    def __init__(self, system_output):
        self.system_controllerfs : [SystemControllerFSObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                controller_fs = SystemControllerFSObject(
                    value['UUID'],
                    value['FS Name'],
                    int(value['Size in GiB']) if value['Size in GiB'] else 0,
                    value['Logical Volume'],
                    value['Replicated'].lower() == 'true',
                )
                self.system_controllerfs.append(controller_fs)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_filesystems(self):
        return self.system_controllerfs

    @staticmethod
    def is_valid_output(value):
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
        if 'Replicated' not in value:
            get_logger().log_error(f'Replicated is not in the output value: {value}')
            valid = False
        return valid

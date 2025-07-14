from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.host.objects.system_host_fs_object import SystemHostFSObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHostFSOutput:
    """
    This class represents a system host-fs-list as an object.

    This is typically a line in the system host-fs-list output table.
    """

    def __init__(self, system_output: list[str]):
        """
        Constructor

        Args:
            system_output (list[str]): output of 'system host-fs-list' command.

        Raises:
            KeywordException: "The output line value was not valid"
        """
        self.system_host_fs: [SystemHostFSObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                host_fs = SystemHostFSObject(
                    value["UUID"],
                    value["FS Name"],
                    int(value["Size in GiB"]) if value["Size in GiB"] else 0,
                    value["Logical Volume"],
                    value["State"],
                )
                if "Capabilities" in value:
                    host_fs.set_capabilities(value["Capabilities"])
                self.system_host_fs.append(host_fs)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_filesystems(self) -> list[SystemHostFSObject]:
        """
        This function is to return the list of host filesystems

        Returns:
            list[SystemHostFSObject]: list of objects representing each row of the table displayed as the result of executing the
        'system host-fs-list {hostname}' command.
        """
        return self.system_host_fs

    @staticmethod
    def is_valid_output(value):
        """
        This function is to check if the output contains all the expected fields.

        """
        valid = True
        if "UUID" not in value:
            get_logger().log_error(f"UUID is not in the output value: {value}")
            valid = False
        if "FS Name" not in value:
            get_logger().log_error(f"FS Name is not in the output value: {value}")
            valid = False
        if "Size in GiB" not in value:
            get_logger().log_error(f"Size is not in the output value: {value}")
            valid = False
        if "Logical Volume" not in value:
            get_logger().log_error(f"Logical Volume is not in the output value: {value}")
            valid = False
        if "State" not in value:
            get_logger().log_error(f"State is not in the output value: {value}")
            valid = False
        return valid

    def get_system_host_fs(self, fs_name: str) -> SystemHostFSObject:
        """
        Gets the given filesystem

        Args:
            fs_name (str): the name of the fs

        Raises:
            ValueError: the given name is not exist

        Returns:
            SystemHostFSObject: the given fs object
        """
        fs_lists = list(filter(lambda item: item.get_name() == fs_name, self.system_host_fs))
        if len(fs_lists) == 0:
            raise ValueError(f"No application with name {fs_name} was found.")
        return fs_lists[0]

    def is_fs_exist(self, fs_name: str) -> bool:
        """
        Check whether the given filesystem exist in the host

        Args:
             fs_name (str): the name of the fs

        Returns:
             bool: True if backend configured; False otherwise.
        """
        fs_lists = list(filter(lambda item: item.get_name() == fs_name, self.system_host_fs))
        if len(fs_lists) == 0:
            return False
        return True

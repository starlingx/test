from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.ceph.objects.system_ceph_mon_object import SystemCephMonObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

class SystemCephMonOutput:
    """
    This class parses the output of 'system ceph-mon-list' command into an object of type SystemCephMonObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system ceph-mon-list' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        self.system_ceph_mon : [SystemCephMonObject] = []
        system_table_parser = SystemTableParser(system_output)
        output_values = system_table_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                system_ceph_mon = SystemCephMonObject()
                system_ceph_mon.set_uuid(value['uuid'])
                system_ceph_mon.set_ceph_mon_gib(value['ceph_mon_gib'])
                system_ceph_mon.set_hostname(value['hostname'])
                system_ceph_mon.set_state(value['state'])
                system_ceph_mon.set_task(value['task'])
                self.system_ceph_mon.append(system_ceph_mon)
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_system_ceph_mon_list(self):
        """
        Returns the parsed system ceph_mon_list object.

        Returns:
        SystemCephMonObject: The parsed system ceph-mon object.
        """

        return self.system_ceph_mon

    @staticmethod
    def is_valid_output(value):
        """
        Checks if the output contains all the expected fields.

        Args:
        value (dict): The dictionary of output values.

        Returns:
        bool: True if the output contains all required fields, False otherwise.
        """

        required_fields = ["uuid", "ceph_mon_gib", "hostname", "state", "task"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid

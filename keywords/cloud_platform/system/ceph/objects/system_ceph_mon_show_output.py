from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.system.ceph.objects.system_ceph_mon_object import SystemCephMonObject
from keywords.cloud_platform.system.system_vertical_table_parser import SystemVerticalTableParser

class SystemCephMonShowOutput:
    """
    This class parses the output of 'system ceph-mon-show' command into an object of type SystemCephMonObject.
    """

    def __init__(self, system_output):
        """
        Constructor

        Args:
        system_output (str): Output of the 'system ceph-mon-show' command.

        Raises:
        KeywordException: If the output is not valid.
        """

        system_vertical_table_parser = SystemVerticalTableParser(system_output)
        output_values = system_vertical_table_parser.get_output_values_dict()

        if self.is_valid_output(output_values):
            self.system_ceph_mon = SystemCephMonObject()
            self.system_ceph_mon.set_uuid(output_values['uuid'])
            self.system_ceph_mon.set_ceph_mon_gib(output_values['ceph_mon_gib'])
            self.system_ceph_mon.set_state(output_values['state'])
            self.system_ceph_mon.set_task(output_values['task'])
            self.system_ceph_mon.set_created_at(output_values['created_at'])
            self.system_ceph_mon.set_updated_at(output_values['updated_at'])
        else:
            raise KeywordException(f"The output line {output_values} was not valid")

    def get_system_ceph_mon_show(self):
        """
        Returns the parsed system ceph-mon object.

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

        required_fields = ["uuid", "ceph_mon_gib", "state", "task", "created_at",
                           "updated_at"]
        valid = True
        for field in required_fields:
            if field not in value:
                get_logger().log_error(f'{field} is not in the output value')
                valid = False
                break
        return valid

from keywords.ceph.ceph_status_section_table_parser import CephStatusSectionTableParser
from keywords.ceph.object.ceph_status_io_object import CephIOObject


class CephIOOutput:
    """
    This class parses the output of Ceph IO

    Example:
        io:
          client:   853 B/s rd, 1 op/s rd, 0 op/s wr

    """

    def __init__(self, ceph_io_output: list[str]):
        """
        Constructor.

            Create an internal CephIOObject.

        Args:
            ceph_io_output (list[str]): a list of strings representing the io output

        """
        ceph_table_parser = CephStatusSectionTableParser(ceph_io_output)
        output_values = ceph_table_parser.get_output_values_dict()
        self.ceph_io_object = CephIOObject()

        if "client" in output_values:
            self.ceph_io_object.client = output_values["client"]

    def get_ceph_io_object(self) -> CephIOObject:
        """
        Getter for CephIOObject object.

        Returns (CephIOObject):
            A CephIOObject

        """
        return self.ceph_io_object

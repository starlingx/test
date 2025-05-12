from keywords.ceph.ceph_status_section_table_parser import CephStatusSectionTableParser
from keywords.ceph.object.ceph_status_services_object import CephServicesObject


class CephServicesOutput:
    """
    This class parses the output of Services

    Example:
         services:
            mon: 3 daemons, quorum a,b,c (age 3w)
            mgr: b(active, since 19h), standbys: c, a
            mds: 1/1 daemons up, 1 hot standby
            osd: 5 osds: 5 up (since 2w), 5 in (since 2w)

    """

    def __init__(self, ceph_services_output: list[str]):
        """
        Constructor.

            Create an internal CephServicesObject.

        Args:
            ceph_services_output (list[str]): a list of strings representing the services output

        """
        ceph_table_parser = CephStatusSectionTableParser(ceph_services_output)
        output_values = ceph_table_parser.get_output_values_dict()
        self.ceph_services_object = CephServicesObject()

        if "mon" in output_values:
            self.ceph_services_object.mon = output_values["mon"]

        if "mgr" in output_values:
            self.ceph_services_object.mgr = output_values["mgr"]

        if "mds" in output_values:
            self.ceph_services_object.mds = output_values["mds"]

        if "osd" in output_values:
            self.ceph_services_object.osd = output_values["osd"]

    def get_ceph_services_object(self) -> CephServicesObject:
        """
        Getter for CephServicesObject object.

        Returns (CephServicesObject):
            A CephServicesObject

        """
        return self.ceph_services_object

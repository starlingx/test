from keywords.ceph.ceph_status_section_table_parser import CephStatusSectionTableParser
from keywords.ceph.object.ceph_status_data_object import CephDataObject


class CephDataOutput:
    """
    This class parses the output of Ceph Data

    Example:
          data:
            volumes: 1/1 healthy
            pools:   4 pools, 112 pgs
            objects: 26 objects, 6.6 MiB
            usage:   400 MiB used, 2.2 TiB / 2.2 TiB avail
            pgs:     112 active+clean

    """

    def __init__(self, ceph_data_output: list[str]):
        """
        Constructor.

            Create an internal DataObject.

        Args:
            ceph_data_output (list[str]): a list of strings representing the data output

        """
        ceph_table_parser = CephStatusSectionTableParser(ceph_data_output)
        output_values = ceph_table_parser.get_output_values_dict()
        self.ceph_data_object = CephDataObject()

        if "volumes" in output_values:
            self.ceph_data_object.volumes = output_values["volumes"]

        if "pools" in output_values:
            self.ceph_data_object.pools = output_values["pools"]

        if "objects" in output_values:
            self.ceph_data_object.objects = output_values["objects"]

        if "usage" in output_values:
            self.ceph_data_object.usage = output_values["usage"]

        if "pgs" in output_values:
            self.ceph_data_object.pgs = output_values["pgs"]

    def get_ceph_data_object(self) -> CephDataObject:
        """
        Getter for CephDataObject object.

        Returns (CephDataObject):
            A CephDataObject

        """
        return self.ceph_data_object

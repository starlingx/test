from keywords.ceph.ceph_status_section_table_parser import CephStatusSectionTableParser
from keywords.ceph.object.ceph_status_cluster_object import CephClusterObject


class CephClusterOutput:
    """
    This class parses the output of Ceph Cluster

    Example:
        id:     8abb43ce-6775-4a1a-99c4-12f37101410e
        health: HEALTH_WARN
                2 MDSs report slow metadata IOs
                Reduced data availability: 48 pgs inactive
                Degraded data redundancy: 66/196 objects degraded (33.673%), 11 pgs degraded, 48 pgs undersized

        OR

        id:     8abb43ce-6775-4a1a-99c4-12f37101410e
        health: HEALTH_OK

    """

    def __init__(self, ceph_cluster_output: list[str]):
        """
        Constructor

            Create an internal CephClusterObject.

        Args:
            ceph_cluster_output (list[str]): a list of strings representing the cluster output

        """
        ceph_table_parser = CephStatusSectionTableParser(ceph_cluster_output)
        output_values = ceph_table_parser.get_output_values_dict()
        self.ceph_cluster_object = CephClusterObject()

        if "id" in output_values:
            self.ceph_cluster_object.id = output_values["id"]

        if "health" in output_values:
            self.ceph_cluster_object.health = output_values["health"]

    def get_ceph_cluster_object(self) -> CephClusterObject:
        """
        Getter for CephClusterObject object.

        Returns (CephClusterObject):
            A CephClusterObject

        """
        return self.ceph_cluster_object

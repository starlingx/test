from keywords.ceph.ceph_osd_pool_ls_detail_table_parser import CephOsdPoolLsDetailTableParser
from keywords.ceph.object.ceph_osd_pool_ls_detail_object import CephOsdPoolLsDetailObject


class CephOsdPoolLsDetailOutput:
    """
    This class parses the output of the command 'ceph osd pool la detail'

    The parsing result is a 'CephOsdPoolLsDetailObject' instance.

    Example:
        'ceph osd pool ls detail'
        pool 1 '.mgr' replicated size 2 min_size 1 crush_rule 9 object_hash rjenkins pg_num 32 pgp_num 32 autoscale_mode
        on last_change 119 lfor 0/0/28 flags hashpspool stripe_width 0 application mgr read_balance_score 1.25
        pool 2 'kube-cephfs-metadata' replicated size 2 min_size 1 crush_rule 11 object_hash rjenkins pg_num 16 pgp_num
        16 autoscale_mode on last_change 122 lfor 0/0/28 flags hashpspool stripe_width 0 pg_autoscale_bias 4 pg_num_min
        16 recovery_priority 5 application cephfs read_balance_score 1.56
        pool 3 'kube-rbd' replicated size 2 min_size 1 crush_rule 10 object_hash rjenkins pg_num 32 pgp_num 32
        autoscale_mode on last_change 121 lfor 0/0/30 flags hashpspool,selfmanaged_snaps stripe_width 0 application rbd
        read_balance_score 1.25
        pool 4 'kube-cephfs-data' replicated size 2 min_size 1 crush_rule 12 object_hash rjenkins pg_num 32 pgp_num 32
        autoscale_mode on last_change 123 lfor 0/0/30 flags hashpspool stripe_width 0 application cephfs
        read_balance_score 2.03
        '\n'
    """

    def __init__(self, ceph_osd_pool_ls_detail_output: list[str]):
        """
        Constructor

        This constructor receives a list of strings, resulting from the execution of the command
        ceph osd pool ls detail, and generates a list of CephOsdPoolLsDetailObject objects.

        Args:
            ceph_osd_pool_ls_detail_output (list[str]): list of strings resulting from the execution of the command `ceph osd pool ls detail`.

        """
        ceph_osd_pool_table_parser = CephOsdPoolLsDetailTableParser(ceph_osd_pool_ls_detail_output)
        output_values = ceph_osd_pool_table_parser.get_output_values_list()
        self.ceph_osd_pool_ls_detail_objects: list[CephOsdPoolLsDetailObject] = []
        for item_list in output_values:
            ceph_osd_pool_ls_detail_object = CephOsdPoolLsDetailObject()
            ceph_osd_pool_ls_detail_object.pool_id = item_list["pool_id"]
            ceph_osd_pool_ls_detail_object.pool_name = item_list["pool_name"]
            ceph_osd_pool_ls_detail_object.replicated_size = item_list["replicated_size"]
            ceph_osd_pool_ls_detail_object.min_size = item_list["min_size"]
            self.ceph_osd_pool_ls_detail_objects.append(ceph_osd_pool_ls_detail_object)

    def get_ceph_osd_pool_list(self):
        """
        Gets the list of `CephOsdPoolLsDetailObject` objects.

        Args: none.

        Returns (list): The list of `CephOsdPoolLsDetailObject` objects.

        """
        return self.ceph_osd_pool_ls_detail_objects

    def get_ceph_osd_pool(self, pool_name: str) -> CephOsdPoolLsDetailObject:
        """
        This function will get the pool with the name specified from this get_ceph_osd_pool_list.

        Args:
            pool_name (str): The name of the pool of interest.

        Returns:
            CephOsdPoolLsDetailObject: The pool object with the name specified.

        Raises:
            ValueError: If the pool with the specified name does not exist in the output.
        """
        for pool_object in self.ceph_osd_pool_ls_detail_objects:
            if pool_object.get_pool_name() == pool_name:
                return pool_object
        else:
            raise ValueError(f"There is no pool with the name {pool_name}.")

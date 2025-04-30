class CephOsdPoolLsDetailObject:
    """
    Class to handle the data provided by the 'ceph osd pool ls detail' command execution.

    This command generates the
    output table shown below, where each object of this class represents a single row in that table.

    'ceph osd pool ls detail'
    pool 1 '.mgr' replicated size 2 min_size 1 crush_rule 9 object_hash rjenkins pg_num 32 pgp_num 32 autoscale_mode on
    last_change 119 lfor 0/0/28 flags hashpspool stripe_width 0 application mgr read_balance_score 1.25
    pool 2 'kube-cephfs-metadata' replicated size 2 min_size 1 crush_rule 11 object_hash rjenkins pg_num 16 pgp_num 16
    autoscale_mode on last_change 122 lfor 0/0/28 flags hashpspool stripe_width 0 pg_autoscale_bias 4 pg_num_min 16
    recovery_priority 5 application cephfs read_balance_score 1.56
    pool 3 'kube-rbd' replicated size 2 min_size 1 crush_rule 10 object_hash rjenkins pg_num 32 pgp_num 32
    autoscale_mode on last_change 121 lfor 0/0/30 flags hashpspool,selfmanaged_snaps stripe_width 0 application rbd
    read_balance_score 1.25
    pool 4 'kube-cephfs-data' replicated size 2 min_size 1 crush_rule 12 object_hash rjenkins pg_num 32 pgp_num 32
    autoscale_mode on last_change 123 lfor 0/0/30 flags hashpspool stripe_width 0 application cephfs
    read_balance_score 2.03
    '\n'

    """

    def __init__(self):
        self.pool_id = -1
        self.pool_name = None
        self.replicated_size = -1
        self.min_size = -1

    def get_pool_id(self) -> int:
        """
        Getter for pool id like: 1; 2; 3 etc.

        Returns: pool int

        """
        return self.pool_id

    def get_pool_name(self) -> str:
        """
        Getter for pool name like: ".mgr"; "kube-cephfs-metadata"; "kube-rbd"; "kube-cephfs-data"

        Returns: pool name

        """
        return self.pool_name

    def get_replicated_size(self) -> int:
        """
        Getter for replicated size

        Returns: replicated size

        """
        return self.replicated_size

    def get_min_size(self) -> int:
        """
        Getter for min_size

        Returns: min_size

        """
        return self.min_size

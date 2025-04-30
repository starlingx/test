class CephOsdPoolLsDetailTableParser:
    """
    Class for "ceph osd pool ls detail" table parsing.

    The "ceph osd pool ls detail" table is a string formatted as a table, resulting from the execution of the command
    'ceph osd pool ls detail' in a Linux terminal.
    This class receives a "ceph osd pool ls detail" table, as shown below, in its constructor and returns a list of dictionaries.
    Each of these dictionaries has the following keys:
        1) pool_id;
        2) pool_name;
        3) replicated_size;
        4) min_size;
        could create more if needed

    An example of a "ceph osd pool ls detail" table:

    pool 1 '.mgr' replicated size 2 min_size 1 crush_rule 9 object_hash rjenkins pg_num 32 pgp_num 32 autoscale_mode
    on last_change 119 lfor 0/0/28 flags hashpspool stripe_width 0 application mgr read_balance_score 1.25
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

    Note: 1) The table has no headers. We can learn about the headers through the names of the dictionary keys.
          2) there is '\n' at the end of the table

    """

    def __init__(self, command_output):
        self.command_output = command_output

    def get_output_values_list(self):
        """
        Getter for output values list.

        Returns: the output values list as a list of dictionaries with the following keys:
            1) pool_id;
            2) pool_name;
            3) replicated_size;
            4) min_size;

        """
        if not self.command_output:
            return []

        # remove '\n' from output
        cleaned_list = [item for item in self.command_output if item != "\n"]
        output_values = []
        for line in cleaned_list:
            values = line.split()
            list_item = {
                "pool_id": int(values[1].strip()),
                "pool_name": values[2].strip().replace("'", ""),
                "replicated_size": int(values[5].strip()),
                "min_size": int(values[7].strip()),
            }
            output_values.append(list_item)

        return output_values

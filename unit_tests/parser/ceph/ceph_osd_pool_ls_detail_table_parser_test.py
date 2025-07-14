from keywords.ceph.object.ceph_osd_pool_ls_detail_output import CephOsdPoolLsDetailOutput

ceph_osd_pool_ls_detail_cmd_output = ["pool 1 '.mgr' replicated size 2 min_size 1 crush_rule 9 object_hash rjenkins pg_num 32 pgp_num 32 autoscale_mode on last_change 119 lfor 0/0/28 flags hashpspool stripe_width 0 application mgr read_balance_score 1.25", "pool 2 'kube-cephfs-metadata' replicated size 2 min_size 1 crush_rule 11 object_hash rjenkins pg_num 16 pgp_num 16 autoscale_mode on last_change 122 lfor 0/0/28 flags hashpspool stripe_width 0 pg_autoscale_bias 4 pg_num_min 16 recovery_priority 5 application cephfs read_balance_score 1.56", "pool 3 'kube-rbd' replicated size 2 min_size 1 crush_rule 10 object_hash rjenkins pg_num 32 pgp_num 32 autoscale_mode on last_change 121 lfor 0/0/30 flags hashpspool,selfmanaged_snaps stripe_width 0 application rbd read_balance_score 1.25", "pool 4 'kube-cephfs-data' replicated size 2 min_size 1 crush_rule 12 object_hash rjenkins pg_num 32 pgp_num 32 autoscale_mode on last_change 123 lfor 0/0/30 flags hashpspool stripe_width 0 application cephfs read_balance_score 2.03", "\n"]


def test_ceph_osd_pool_ls_detail_output_parser():
    """
    Tests the "ceph osd pool ls detail" parser with a well formated input table.

    In this case, the parser must
    be able to correctly generate a list of dictionaries.

    """
    ceph_osd_pool_ls_detail_output = CephOsdPoolLsDetailOutput(ceph_osd_pool_ls_detail_cmd_output)
    ceph_osd_pool_objects = ceph_osd_pool_ls_detail_output.get_ceph_osd_pool_list()
    assert len(ceph_osd_pool_objects), 4

    mgr_object = ceph_osd_pool_ls_detail_output.get_ceph_osd_pool(".mgr")
    assert mgr_object.get_pool_id() == 1
    assert mgr_object.get_pool_name() == ".mgr"
    assert mgr_object.get_replicated_size() == 2
    assert mgr_object.get_min_size() == 1

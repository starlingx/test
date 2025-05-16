from keywords.ceph.object.ceph_status_output import CephStatusOutput

# fmt: off
ceph_s_health_warning = [
    "  cluster:\n",
    "    id:     001ab3d8-1f02-4294-b594-e2b216b9b2dc\n",
    "    health: HEALTH_WARN\n",
    "            2 MDSs report slow metadata IOs\n",
    "            Reduced data availability: 48 pgs inactive\n",
    "            Degraded data redundancy: 66/196 objects degraded (33.673%), 11 pgs degraded, 48 pgs undersized\n",
    " \n",
    "  services:\n",
    "    mon: 2 daemons, quorum a,b,c (age 4w)\n",
    "    mgr: b(active, since 9d), standbys: c, a\n",
    "    mds: 1/1 daemons up, 1 hot standby\n",
    "    osd: 3 osds: 3 up (since 3w), 3 in (since 3w)\n",
    " \n",
    "  data:\n",
    "    volumes: 1/1 healthy\n",
    "    pools:   4 pools, 112 pgs\n",
    "    objects: 27 objects, 9.1 MiB\n",
    "    usage:   425 MiB used, 2.2 TiB / 2.2 TiB avail\n",
    "    pgs:     112 active+clean\n",
    " \n",
    "  io:\n",
    "    client:   1.2 KiB/s rd, 2 op/s rd, 0 op/s wr\n",
    " \n"
]

# fmt: off
ceph_s_health_ok = [
    "  cluster:\n",
    "    id:     8abb43ce-6775-4a1a-99c4-12f37101410e\n",
    "    health: HEALTH_OK\n",
    " \n",
    "  services:\n",
    "    mon: 3 daemons, quorum a,b,c (age 4w)\n",
    "    mgr: b(active, since 9d), standbys: c, a\n",
    "    mds: 1/1 daemons up, 1 hot standby\n",
    "    osd: 5 osds: 5 up (since 3w), 5 in (since 3w)\n",
    " \n",
    "  data:\n",
    "    volumes: 1/1 healthy\n",
    "    pools:   4 pools, 112 pgs\n",
    "    objects: 27 objects, 9.1 MiB\n",
    "    usage:   425 MiB used, 2.2 TiB / 2.2 TiB avail\n",
    "    pgs:     112 active+clean\n",
    " \n",
    "  io:\n",
    "    client:   1.2 KiB/s rd, 2 op/s rd, 0 op/s wr\n",
    " \n"
]


def test_ceph_status_output():
    """
    Tests ceph_status_output functions

        include:
            is_ceph_healthy()
            get_ceph_osd_count()
            get_ceph_mon_count()

    """
    ceph_s_health_ok_output = CephStatusOutput(ceph_s_health_ok)
    cluster_object = ceph_s_health_ok_output.get_ceph_cluster_output().get_ceph_cluster_object()
    assert cluster_object.get_id() == "8abb43ce-6775-4a1a-99c4-12f37101410e"
    assert cluster_object.get_health() == "HEALTH_OK"
    assert ceph_s_health_ok_output.get_ceph_osd_count() == 5
    assert ceph_s_health_ok_output.get_ceph_mon_count() == 3

    ceph_s_health_status = ceph_s_health_ok_output.is_ceph_healthy()
    if not ceph_s_health_status:
        raise ValueError("Error output")

    ceph_s_health_warn_output = CephStatusOutput(ceph_s_health_warning)
    cluster_object = ceph_s_health_warn_output.get_ceph_cluster_output().get_ceph_cluster_object()
    assert cluster_object.get_id() == "001ab3d8-1f02-4294-b594-e2b216b9b2dc"
    assert cluster_object.get_health() == "HEALTH_WARN; 2 MDSs report slow metadata IOs; Reduced data availability: 48 pgs inactive; Degraded data redundancy: 66/196 objects degraded (33.673%), 11 pgs degraded, 48 pgs undersized"
    assert ceph_s_health_warn_output.get_ceph_osd_count() == 3
    assert ceph_s_health_warn_output.get_ceph_mon_count() == 2
    ceph_s_health_status = ceph_s_health_warn_output.is_ceph_healthy()
    if ceph_s_health_status:
        raise ValueError("Error output")

from keywords.k8s.volumesnapshots.object.kubectl_get_volumesnapshots_table_parser import KubectlGetVolumesnapshotsTableParser


def test_get_volumesnapshots_table_parser():
    """
    Tests the k8s_get_volumesnapshots table parser

    Parser k8s_get_volumesnapshots table
    """
    get_volumesnapshots_output = (
        "NAME                          READYTOUSE   SOURCEPVC   SOURCESNAPSHOTCONTENT   RESTORESIZE   SNAPSHOTCLASS             SNAPSHOTCONTENT                                    CREATIONTIME   AGE\n",
        "mcsi-powerstore-pvc-snapshot  true         pvol0                               8Gi           csi-powerstore-snapshot   snapcontent-02da0df5-3e9e-4981-a693-f7ae7b03db4c   19m            19m\n",
    )

    table_parser = KubectlGetVolumesnapshotsTableParser(get_volumesnapshots_output)
    output_values = table_parser.get_output_values_list()

    assert len(output_values) == 1, "There are two entries in this get volumesnapshots table."
    first_line = output_values[0]

    assert first_line["NAME"] == "mcsi-powerstore-pvc-snapshot"
    assert first_line["READYTOUSE"] == "true"
    assert first_line["SOURCEPVC"] == "pvol0"
    assert first_line["SOURCESNAPSHOTCONTENT"] == ""
    assert first_line["RESTORESIZE"] == "8Gi"
    assert first_line["SNAPSHOTCLASS"] == "csi-powerstore-snapshot"
    assert first_line["SNAPSHOTCONTENT"] == "snapcontent-02da0df5-3e9e-4981-a693-f7ae7b03db4c"
    assert first_line["CREATIONTIME"] == "19m"
    assert first_line["AGE"] == "19m"

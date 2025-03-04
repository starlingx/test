from keywords.cloud_platform.system.storage.objects.system_storage_backend_output import (
    SystemStorageBackendOutput,
)
from keywords.cloud_platform.system.system_table_parser import SystemTableParser

storage_backend_list_ceph_output = ["+--------------------------------------+------------+---------+------------+------+----------+--------------------+\n", "| uuid                                 | name       | backend | state      | task | services | capabilities       |\n", "+--------------------------------------+------------+---------+------------+------+----------+--------------------+\n", "| b3655f85-5e16-471e-b994-c9f910c53f00 | ceph-store | ceph    | configured | None | None     | replication: 2     |\n", "|                                      |            |         |            |      |          | min_replication: 1 |\n", "+--------------------------------------+------------+---------+------------+------+----------+--------------------+\n"]


def test_storage_backend_table_parser():
    """
    Tests the "system storage_backend_list" table parser

    Returns:None
    """
    system_table_parser = SystemTableParser(storage_backend_list_ceph_output)
    output_values = system_table_parser.get_output_values_list()
    assert len(output_values) == 1

    output = output_values[0]
    assert output["uuid"] == "b3655f85-5e16-471e-b994-c9f910c53f00"
    assert output["name"] == "ceph-store"
    assert output["backend"] == "ceph"
    assert output["state"] == "configured"
    assert output["task"] == "None"
    assert output["services"] == "None"
    assert output["capabilities"] == "replication: 2min_replication: 1"

    system_storage_backend_output = SystemStorageBackendOutput(storage_backend_list_ceph_output)
    backend_object = system_storage_backend_output.get_system_storage_backend("ceph")
    assert backend_object.get_uuid() == "b3655f85-5e16-471e-b994-c9f910c53f00"
    assert backend_object.get_name() == "ceph-store"
    assert backend_object.get_backend() == "ceph"
    assert backend_object.get_state() == "configured"
    assert backend_object.get_task() == "None"
    assert backend_object.get_services() == "None"
    assert backend_object.get_capabilities().get_replication() == 2
    assert backend_object.get_capabilities().get_min_replication() == 1

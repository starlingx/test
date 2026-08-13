"""REST API operations without authentication expect 401 Unauthorized."""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.bad_auth.rest_bad_auth_keywords import RestBadAuthKeywords


@mark.p1
def test_bad_auth_get_addrpools_pool_id() -> None:
    """GET /addrpools/{pool_id} without auth returns 401.

    Test Steps:
        - GET /addrpools/{pool_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /addrpools/{pool_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/addrpools/{pool_id}")
    validate_equals(response.get_status_code(), 401, "GET /addrpools/{pool_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_ceph_mon_ceph_mon_id() -> None:
    """GET /ceph_mon/{ceph_mon_id} without auth returns 401.

    Test Steps:
        - GET /ceph_mon/{ceph_mon_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ceph_mon/{ceph_mon_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ceph_mon/{ceph_mon_id}")
    validate_equals(response.get_status_code(), 401, "GET /ceph_mon/{ceph_mon_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_devices_device_id() -> None:
    """GET /devices/{device_id} without auth returns 401.

    Test Steps:
        - GET /devices/{device_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /devices/{device_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/devices/{device_id}")
    validate_equals(response.get_status_code(), 401, "GET /devices/{device_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_event_log_log_uuid() -> None:
    """GET /event_log/{log_uuid} without auth returns 401.

    Test Steps:
        - GET /event_log/{log_uuid} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /event_log/{log_uuid} without auth")
    response = RestBadAuthKeywords().get_without_auth("/event_log/{log_uuid}")
    validate_equals(response.get_status_code(), 401, "GET /event_log/{log_uuid} without auth returns 401")


@mark.p1
def test_bad_auth_get_ialarms_alarm_uuid() -> None:
    """GET /ialarms/{alarm_uuid} without auth returns 401.

    Test Steps:
        - GET /ialarms/{alarm_uuid} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ialarms/{alarm_uuid} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ialarms/{alarm_uuid}")
    validate_equals(response.get_status_code(), 401, "GET /ialarms/{alarm_uuid} without auth returns 401")


@mark.p1
def test_bad_auth_get_icpus_cpu_id() -> None:
    """GET /icpus/{cpu_id} without auth returns 401.

    Test Steps:
        - GET /icpus/{cpu_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /icpus/{cpu_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/icpus/{cpu_id}")
    validate_equals(response.get_status_code(), 401, "GET /icpus/{cpu_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_idisks_disk_id() -> None:
    """GET /idisks/{disk_id} without auth returns 401.

    Test Steps:
        - GET /idisks/{disk_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /idisks/{disk_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/idisks/{disk_id}")
    validate_equals(response.get_status_code(), 401, "GET /idisks/{disk_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_idns() -> None:
    """GET /idns without auth returns 401.

    Test Steps:
        - GET /idns without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /idns without auth")
    response = RestBadAuthKeywords().get_without_auth("/idns")
    validate_equals(response.get_status_code(), 401, "GET /idns without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_bulk_export() -> None:
    """GET /ihosts/bulk_export without auth returns 401.

    Test Steps:
        - GET /ihosts/bulk_export without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/bulk_export without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/bulk_export")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/bulk_export without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_addresses_address_id() -> None:
    """GET /ihosts/{host_id}/addresses/{address_id} without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/addresses/{address_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/addresses/{address_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/addresses/{address_id}")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/addresses/{address_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_addresses() -> None:
    """GET /ihosts/{host_id}/addresses without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/addresses without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/addresses without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/addresses")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/addresses without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_idisks() -> None:
    """GET /ihosts/{host_id}/idisks without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/idisks without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/idisks without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/idisks")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/idisks without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_ilvgs() -> None:
    """GET /ihosts/{host_id}/ilvgs without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/ilvgs without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/ilvgs without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/ilvgs")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/ilvgs without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_imemorys() -> None:
    """GET /ihosts/{host_id}/imemorys without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/imemorys without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/imemorys without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/imemorys")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/imemorys without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_ipvs() -> None:
    """GET /ihosts/{host_id}/ipvs without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/ipvs without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/ipvs without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/ipvs")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/ipvs without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_isensorgroups() -> None:
    """GET /ihosts/{host_id}/isensorgroups without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/isensorgroups without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/isensorgroups without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/isensorgroups")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/isensorgroups without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_isensors() -> None:
    """GET /ihosts/{host_id}/isensors without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/isensors without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/isensors without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/isensors")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/isensors without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_istors() -> None:
    """GET /ihosts/{host_id}/istors without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/istors without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/istors without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/istors")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/istors without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_pci_devices() -> None:
    """GET /ihosts/{host_id}/pci_devices without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/pci_devices without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/pci_devices without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/pci_devices")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/pci_devices without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_routes() -> None:
    """GET /ihosts/{host_id}/routes without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/routes without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/routes without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/routes")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/routes without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id_routes_route_id() -> None:
    """GET /ihosts/{host_id}/routes/{route_id} without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id}/routes/{route_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id}/routes/{route_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}/routes/{route_id}")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id}/routes/{route_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_iinterfaces_interface_id() -> None:
    """GET /iinterfaces/{interface_id} without auth returns 401.

    Test Steps:
        - GET /iinterfaces/{interface_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /iinterfaces/{interface_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/iinterfaces/{interface_id}")
    validate_equals(response.get_status_code(), 401, "GET /iinterfaces/{interface_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_ilvgs_volumegroup_id() -> None:
    """GET /ilvgs/{volumegroup_id} without auth returns 401.

    Test Steps:
        - GET /ilvgs/{volumegroup_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ilvgs/{volumegroup_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ilvgs/{volumegroup_id}")
    validate_equals(response.get_status_code(), 401, "GET /ilvgs/{volumegroup_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_imemorys_memory_id() -> None:
    """GET /imemorys/{memory_id} without auth returns 401.

    Test Steps:
        - GET /imemorys/{memory_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /imemorys/{memory_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/imemorys/{memory_id}")
    validate_equals(response.get_status_code(), 401, "GET /imemorys/{memory_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_ipvs_physicalvolume_id() -> None:
    """GET /ipvs/{physicalvolume_id} without auth returns 401.

    Test Steps:
        - GET /ipvs/{physicalvolume_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ipvs/{physicalvolume_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ipvs/{physicalvolume_id}")
    validate_equals(response.get_status_code(), 401, "GET /ipvs/{physicalvolume_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_isensorgroups_sensorgroup_id() -> None:
    """GET /isensorgroups/{sensorgroup_id} without auth returns 401.

    Test Steps:
        - GET /isensorgroups/{sensorgroup_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /isensorgroups/{sensorgroup_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/isensorgroups/{sensorgroup_id}")
    validate_equals(response.get_status_code(), 401, "GET /isensorgroups/{sensorgroup_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_isensors_sensor_id() -> None:
    """GET /isensors/{sensor_id} without auth returns 401.

    Test Steps:
        - GET /isensors/{sensor_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /isensors/{sensor_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/isensors/{sensor_id}")
    validate_equals(response.get_status_code(), 401, "GET /isensors/{sensor_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_istors_stor_id() -> None:
    """GET /istors/{stor_id} without auth returns 401.

    Test Steps:
        - GET /istors/{stor_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /istors/{stor_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/istors/{stor_id}")
    validate_equals(response.get_status_code(), 401, "GET /istors/{stor_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_lldp_agents_lldp_agent_id() -> None:
    """GET /lldp_agents/{lldp_agent_id} without auth returns 401.

    Test Steps:
        - GET /lldp_agents/{lldp_agent_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /lldp_agents/{lldp_agent_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/lldp_agents/{lldp_agent_id}")
    validate_equals(response.get_status_code(), 401, "GET /lldp_agents/{lldp_agent_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_lldp_neighbours_lldp_neighbor_id() -> None:
    """GET /lldp_neighbours/{lldp_neighbor_id} without auth returns 401.

    Test Steps:
        - GET /lldp_neighbours/{lldp_neighbor_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /lldp_neighbours/{lldp_neighbor_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/lldp_neighbours/{lldp_neighbor_id}")
    validate_equals(response.get_status_code(), 401, "GET /lldp_neighbours/{lldp_neighbor_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_loads_load_id() -> None:
    """GET /loads/{load_id} without auth returns 401.

    Test Steps:
        - GET /loads/{load_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /loads/{load_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/loads/{load_id}")
    validate_equals(response.get_status_code(), 401, "GET /loads/{load_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_networks_network_id() -> None:
    """GET /networks/{network_id} without auth returns 401.

    Test Steps:
        - GET /networks/{network_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /networks/{network_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/networks/{network_id}")
    validate_equals(response.get_status_code(), 401, "GET /networks/{network_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_ports_port_id() -> None:
    """GET /ports/{port_id} without auth returns 401.

    Test Steps:
        - GET /ports/{port_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ports/{port_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ports/{port_id}")
    validate_equals(response.get_status_code(), 401, "GET /ports/{port_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_sdn_controller_controller_id() -> None:
    """GET /sdn_controller/{controller_id} without auth returns 401.

    Test Steps:
        - GET /sdn_controller/{controller_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /sdn_controller/{controller_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/sdn_controller/{controller_id}")
    validate_equals(response.get_status_code(), 401, "GET /sdn_controller/{controller_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_servicegroup_servicegroup_id() -> None:
    """GET /servicegroup/{servicegroup_id} without auth returns 401.

    Test Steps:
        - GET /servicegroup/{servicegroup_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /servicegroup/{servicegroup_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/servicegroup/{servicegroup_id}")
    validate_equals(response.get_status_code(), 401, "GET /servicegroup/{servicegroup_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_servicenodes_node_id() -> None:
    """GET /servicenodes/{node_id} without auth returns 401.

    Test Steps:
        - GET /servicenodes/{node_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /servicenodes/{node_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/servicenodes/{node_id}")
    validate_equals(response.get_status_code(), 401, "GET /servicenodes/{node_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_service_parameter_parameter_id() -> None:
    """GET /service_parameter/{parameter_id} without auth returns 401.

    Test Steps:
        - GET /service_parameter/{parameter_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /service_parameter/{parameter_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/service_parameter/{parameter_id}")
    validate_equals(response.get_status_code(), 401, "GET /service_parameter/{parameter_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_services_service_id() -> None:
    """GET /services/{service_id} without auth returns 401.

    Test Steps:
        - GET /services/{service_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /services/{service_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/services/{service_id}")
    validate_equals(response.get_status_code(), 401, "GET /services/{service_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_storage_lvm() -> None:
    """GET /storage_lvm without auth returns 401.

    Test Steps:
        - GET /storage_lvm without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /storage_lvm without auth")
    response = RestBadAuthKeywords().get_without_auth("/storage_lvm")
    validate_equals(response.get_status_code(), 401, "GET /storage_lvm without auth returns 401")


@mark.p1
def test_bad_auth_get_tpmconfig_tpmconfig_id() -> None:
    """GET /tpmconfig/{tpmconfig_id} without auth returns 401.

    Test Steps:
        - GET /tpmconfig/{tpmconfig_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /tpmconfig/{tpmconfig_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/tpmconfig/{tpmconfig_id}")
    validate_equals(response.get_status_code(), 401, "GET /tpmconfig/{tpmconfig_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_addrpools() -> None:
    """GET /addrpools without auth returns 401.

    Test Steps:
        - GET /addrpools without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /addrpools without auth")
    response = RestBadAuthKeywords().get_without_auth("/addrpools")
    validate_equals(response.get_status_code(), 401, "GET /addrpools without auth returns 401")


@mark.p1
def test_bad_auth_get_ceph_mon() -> None:
    """GET /ceph_mon without auth returns 401.

    Test Steps:
        - GET /ceph_mon without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ceph_mon without auth")
    response = RestBadAuthKeywords().get_without_auth("/ceph_mon")
    validate_equals(response.get_status_code(), 401, "GET /ceph_mon without auth returns 401")


@mark.p1
def test_bad_auth_get_clusters() -> None:
    """GET /clusters without auth returns 401.

    Test Steps:
        - GET /clusters without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /clusters without auth")
    response = RestBadAuthKeywords().get_without_auth("/clusters")
    validate_equals(response.get_status_code(), 401, "GET /clusters without auth returns 401")


@mark.p1
def test_bad_auth_get_clusters_uuid() -> None:
    """GET /clusters/{uuid} without auth returns 401.

    Test Steps:
        - GET /clusters/{uuid} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /clusters/{uuid} without auth")
    response = RestBadAuthKeywords().get_without_auth("/clusters/{uuid}")
    validate_equals(response.get_status_code(), 401, "GET /clusters/{uuid} without auth returns 401")


@mark.p1
def test_bad_auth_get_controller_fs() -> None:
    """GET /controller_fs without auth returns 401.

    Test Steps:
        - GET /controller_fs without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /controller_fs without auth")
    response = RestBadAuthKeywords().get_without_auth("/controller_fs")
    validate_equals(response.get_status_code(), 401, "GET /controller_fs without auth returns 401")


@mark.p1
def test_bad_auth_get_drbdconfig() -> None:
    """GET /drbdconfig without auth returns 401.

    Test Steps:
        - GET /drbdconfig without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /drbdconfig without auth")
    response = RestBadAuthKeywords().get_without_auth("/drbdconfig")
    validate_equals(response.get_status_code(), 401, "GET /drbdconfig without auth returns 401")


@mark.p1
def test_bad_auth_get_event_log() -> None:
    """GET /event_log without auth returns 401.

    Test Steps:
        - GET /event_log without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /event_log without auth")
    response = RestBadAuthKeywords().get_without_auth("/event_log")
    validate_equals(response.get_status_code(), 401, "GET /event_log without auth returns 401")


@mark.p1
def test_bad_auth_get_event_suppression() -> None:
    """GET /event_suppression without auth returns 401.

    Test Steps:
        - GET /event_suppression without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /event_suppression without auth")
    response = RestBadAuthKeywords().get_without_auth("/event_suppression")
    validate_equals(response.get_status_code(), 401, "GET /event_suppression without auth returns 401")


@mark.p1
def test_bad_auth_get_health() -> None:
    """GET /health without auth returns 401.

    Test Steps:
        - GET /health without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /health without auth")
    response = RestBadAuthKeywords().get_without_auth("/health")
    validate_equals(response.get_status_code(), 401, "GET /health without auth returns 401")


@mark.p1
def test_bad_auth_get_health_upgrade() -> None:
    """GET /health/upgrade without auth returns 401.

    Test Steps:
        - GET /health/upgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /health/upgrade without auth")
    response = RestBadAuthKeywords().get_without_auth("/health/upgrade")
    validate_equals(response.get_status_code(), 401, "GET /health/upgrade without auth returns 401")


@mark.p1
def test_bad_auth_get_ialarms() -> None:
    """GET /ialarms without auth returns 401.

    Test Steps:
        - GET /ialarms without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ialarms without auth")
    response = RestBadAuthKeywords().get_without_auth("/ialarms")
    validate_equals(response.get_status_code(), 401, "GET /ialarms without auth returns 401")


@mark.p1
def test_bad_auth_get_iextoam() -> None:
    """GET /iextoam without auth returns 401.

    Test Steps:
        - GET /iextoam without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /iextoam without auth")
    response = RestBadAuthKeywords().get_without_auth("/iextoam")
    validate_equals(response.get_status_code(), 401, "GET /iextoam without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts() -> None:
    """GET /ihosts without auth returns 401.

    Test Steps:
        - GET /ihosts without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts")
    validate_equals(response.get_status_code(), 401, "GET /ihosts without auth returns 401")


@mark.p1
def test_bad_auth_get_ihosts_host_id() -> None:
    """GET /ihosts/{host_id} without auth returns 401.

    Test Steps:
        - GET /ihosts/{host_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts/{host_id} without auth")
    response = RestBadAuthKeywords().get_without_auth("/ihosts/{host_id}")
    validate_equals(response.get_status_code(), 401, "GET /ihosts/{host_id} without auth returns 401")


@mark.p1
def test_bad_auth_get_intp() -> None:
    """GET /intp without auth returns 401.

    Test Steps:
        - GET /intp without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /intp without auth")
    response = RestBadAuthKeywords().get_without_auth("/intp")
    validate_equals(response.get_status_code(), 401, "GET /intp without auth returns 401")


@mark.p1
def test_bad_auth_get_isystems() -> None:
    """GET /isystems without auth returns 401.

    Test Steps:
        - GET /isystems without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /isystems without auth")
    response = RestBadAuthKeywords().get_without_auth("/isystems")
    validate_equals(response.get_status_code(), 401, "GET /isystems without auth returns 401")


@mark.p1
def test_bad_auth_get_lldp_agents() -> None:
    """GET /lldp_agents without auth returns 401.

    Test Steps:
        - GET /lldp_agents without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /lldp_agents without auth")
    response = RestBadAuthKeywords().get_without_auth("/lldp_agents")
    validate_equals(response.get_status_code(), 401, "GET /lldp_agents without auth returns 401")


@mark.p1
def test_bad_auth_get_lldp_neighbours() -> None:
    """GET /lldp_neighbours without auth returns 401.

    Test Steps:
        - GET /lldp_neighbours without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /lldp_neighbours without auth")
    response = RestBadAuthKeywords().get_without_auth("/lldp_neighbours")
    validate_equals(response.get_status_code(), 401, "GET /lldp_neighbours without auth returns 401")


@mark.p1
def test_bad_auth_get_loads() -> None:
    """GET /loads without auth returns 401.

    Test Steps:
        - GET /loads without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /loads without auth")
    response = RestBadAuthKeywords().get_without_auth("/loads")
    validate_equals(response.get_status_code(), 401, "GET /loads without auth returns 401")


@mark.p1
def test_bad_auth_get_networks() -> None:
    """GET /networks without auth returns 401.

    Test Steps:
        - GET /networks without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /networks without auth")
    response = RestBadAuthKeywords().get_without_auth("/networks")
    validate_equals(response.get_status_code(), 401, "GET /networks without auth returns 401")


@mark.p1
def test_bad_auth_get_remotelogging() -> None:
    """GET /remotelogging without auth returns 401.

    Test Steps:
        - GET /remotelogging without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /remotelogging without auth")
    response = RestBadAuthKeywords().get_without_auth("/remotelogging")
    validate_equals(response.get_status_code(), 401, "GET /remotelogging without auth returns 401")


@mark.p1
def test_bad_auth_get_servicegroup() -> None:
    """GET /servicegroup without auth returns 401.

    Test Steps:
        - GET /servicegroup without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /servicegroup without auth")
    response = RestBadAuthKeywords().get_without_auth("/servicegroup")
    validate_equals(response.get_status_code(), 401, "GET /servicegroup without auth returns 401")


@mark.p1
def test_bad_auth_get_servicenodes() -> None:
    """GET /servicenodes without auth returns 401.

    Test Steps:
        - GET /servicenodes without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /servicenodes without auth")
    response = RestBadAuthKeywords().get_without_auth("/servicenodes")
    validate_equals(response.get_status_code(), 401, "GET /servicenodes without auth returns 401")


@mark.p1
def test_bad_auth_get_service_parameter() -> None:
    """GET /service_parameter without auth returns 401.

    Test Steps:
        - GET /service_parameter without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /service_parameter without auth")
    response = RestBadAuthKeywords().get_without_auth("/service_parameter")
    validate_equals(response.get_status_code(), 401, "GET /service_parameter without auth returns 401")


@mark.p1
def test_bad_auth_get_services() -> None:
    """GET /services without auth returns 401.

    Test Steps:
        - GET /services without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /services without auth")
    response = RestBadAuthKeywords().get_without_auth("/services")
    validate_equals(response.get_status_code(), 401, "GET /services without auth returns 401")


@mark.p1
def test_bad_auth_get_storage_backend() -> None:
    """GET /storage_backend without auth returns 401.

    Test Steps:
        - GET /storage_backend without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /storage_backend without auth")
    response = RestBadAuthKeywords().get_without_auth("/storage_backend")
    validate_equals(response.get_status_code(), 401, "GET /storage_backend without auth returns 401")


@mark.p1
def test_bad_auth_get_storage_backend_usage() -> None:
    """GET /storage_backend/usage without auth returns 401.

    Test Steps:
        - GET /storage_backend/usage without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /storage_backend/usage without auth")
    response = RestBadAuthKeywords().get_without_auth("/storage_backend/usage")
    validate_equals(response.get_status_code(), 401, "GET /storage_backend/usage without auth returns 401")


@mark.p1
def test_bad_auth_get_storage_ceph() -> None:
    """GET /storage_ceph without auth returns 401.

    Test Steps:
        - GET /storage_ceph without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /storage_ceph without auth")
    response = RestBadAuthKeywords().get_without_auth("/storage_ceph")
    validate_equals(response.get_status_code(), 401, "GET /storage_ceph without auth returns 401")


@mark.p1
def test_bad_auth_get_iinfra() -> None:
    """GET /iinfra without auth returns 401.

    Test Steps:
        - GET /iinfra without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /iinfra without auth")
    response = RestBadAuthKeywords().get_without_auth("/iinfra")
    validate_equals(response.get_status_code(), 401, "GET /iinfra without auth returns 401")


@mark.p1
def test_bad_auth_get_ipm() -> None:
    """GET /ipm without auth returns 401.

    Test Steps:
        - GET /ipm without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ipm without auth")
    response = RestBadAuthKeywords().get_without_auth("/ipm")
    validate_equals(response.get_status_code(), 401, "GET /ipm without auth returns 401")


@mark.p1
def test_bad_auth_get_istorconfig() -> None:
    """GET /istorconfig without auth returns 401.

    Test Steps:
        - GET /istorconfig without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /istorconfig without auth")
    response = RestBadAuthKeywords().get_without_auth("/istorconfig")
    validate_equals(response.get_status_code(), 401, "GET /istorconfig without auth returns 401")


@mark.p1
def test_bad_auth_get_sdn_controller() -> None:
    """GET /sdn_controller without auth returns 401.

    Test Steps:
        - GET /sdn_controller without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /sdn_controller without auth")
    response = RestBadAuthKeywords().get_without_auth("/sdn_controller")
    validate_equals(response.get_status_code(), 401, "GET /sdn_controller without auth returns 401")


@mark.p1
def test_bad_auth_get_tpmconfig() -> None:
    """GET /tpmconfig without auth returns 401.

    Test Steps:
        - GET /tpmconfig without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /tpmconfig without auth")
    response = RestBadAuthKeywords().get_without_auth("/tpmconfig")
    validate_equals(response.get_status_code(), 401, "GET /tpmconfig without auth returns 401")


@mark.p1
def test_bad_auth_get_upgrade() -> None:
    """GET /upgrade without auth returns 401.

    Test Steps:
        - GET /upgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /upgrade without auth")
    response = RestBadAuthKeywords().get_without_auth("/upgrade")
    validate_equals(response.get_status_code(), 401, "GET /upgrade without auth returns 401")


@mark.p1
def test_bad_auth_delete_addrpools_pool_id() -> None:
    """DELETE /addrpools/{pool_id} without auth returns 401.

    Test Steps:
        - DELETE /addrpools/{pool_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /addrpools/{pool_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/addrpools/{pool_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /addrpools/{pool_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_ihosts_host_id_addresses_address_id() -> None:
    """DELETE /ihosts/{host_id}/addresses/{address_id} without auth returns 401.

    Test Steps:
        - DELETE /ihosts/{host_id}/addresses/{address_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /ihosts/{host_id}/addresses/{address_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/ihosts/{host_id}/addresses/{address_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /ihosts/{host_id}/addresses/{address_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_ihosts_host_id_routes_route_id() -> None:
    """DELETE /ihosts/{host_id}/routes/{route_id} without auth returns 401.

    Test Steps:
        - DELETE /ihosts/{host_id}/routes/{route_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /ihosts/{host_id}/routes/{route_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/ihosts/{host_id}/routes/{route_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /ihosts/{host_id}/routes/{route_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_iinterfaces_interface_id() -> None:
    """DELETE /iinterfaces/{interface_id} without auth returns 401.

    Test Steps:
        - DELETE /iinterfaces/{interface_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /iinterfaces/{interface_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/iinterfaces/{interface_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /iinterfaces/{interface_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_ilvgs_volumegroup_id() -> None:
    """DELETE /ilvgs/{volumegroup_id} without auth returns 401.

    Test Steps:
        - DELETE /ilvgs/{volumegroup_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /ilvgs/{volumegroup_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/ilvgs/{volumegroup_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /ilvgs/{volumegroup_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_ipvs_physicalvolume_id() -> None:
    """DELETE /ipvs/{physicalvolume_id} without auth returns 401.

    Test Steps:
        - DELETE /ipvs/{physicalvolume_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /ipvs/{physicalvolume_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/ipvs/{physicalvolume_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /ipvs/{physicalvolume_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_istors_stor_id() -> None:
    """DELETE /istors/{stor_id} without auth returns 401.

    Test Steps:
        - DELETE /istors/{stor_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /istors/{stor_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/istors/{stor_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /istors/{stor_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_loads_load_id() -> None:
    """DELETE /loads/{load_id} without auth returns 401.

    Test Steps:
        - DELETE /loads/{load_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /loads/{load_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/loads/{load_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /loads/{load_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_sdn_controller_controller_id() -> None:
    """DELETE /sdn_controller/{controller_id} without auth returns 401.

    Test Steps:
        - DELETE /sdn_controller/{controller_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /sdn_controller/{controller_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/sdn_controller/{controller_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /sdn_controller/{controller_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_service_parameter_parameter_id() -> None:
    """DELETE /service_parameter/{parameter_id} without auth returns 401.

    Test Steps:
        - DELETE /service_parameter/{parameter_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /service_parameter/{parameter_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/service_parameter/{parameter_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /service_parameter/{parameter_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_tpmconfig_tpmconfig_id() -> None:
    """DELETE /tpmconfig/{tpmconfig_id} without auth returns 401.

    Test Steps:
        - DELETE /tpmconfig/{tpmconfig_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /tpmconfig/{tpmconfig_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/tpmconfig/{tpmconfig_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /tpmconfig/{tpmconfig_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_ialarms_alarm_uuid() -> None:
    """DELETE /ialarms/{alarm_uuid} without auth returns 401.

    Test Steps:
        - DELETE /ialarms/{alarm_uuid} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /ialarms/{alarm_uuid} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/ialarms/{alarm_uuid}")
    validate_equals(response.get_status_code(), 401, "DELETE /ialarms/{alarm_uuid} without auth returns 401")


@mark.p1
def test_bad_auth_delete_ihosts_host_id() -> None:
    """DELETE /ihosts/{host_id} without auth returns 401.

    Test Steps:
        - DELETE /ihosts/{host_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /ihosts/{host_id} without auth")
    response = RestBadAuthKeywords().delete_without_auth("/ihosts/{host_id}")
    validate_equals(response.get_status_code(), 401, "DELETE /ihosts/{host_id} without auth returns 401")


@mark.p1
def test_bad_auth_delete_upgrade() -> None:
    """DELETE /upgrade without auth returns 401.

    Test Steps:
        - DELETE /upgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("DELETE /upgrade without auth")
    response = RestBadAuthKeywords().delete_without_auth("/upgrade")
    validate_equals(response.get_status_code(), 401, "DELETE /upgrade without auth returns 401")


@mark.p1
def test_bad_auth_patch_addrpools_pool_id() -> None:
    """PATCH /addrpools/{pool_id} without auth returns 401.

    Test Steps:
        - PATCH /addrpools/{pool_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /addrpools/{pool_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/addrpools/{pool_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /addrpools/{pool_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_ceph_mon_ceph_mon_id() -> None:
    """PATCH /ceph_mon/{ceph_mon_id} without auth returns 401.

    Test Steps:
        - PATCH /ceph_mon/{ceph_mon_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /ceph_mon/{ceph_mon_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/ceph_mon/{ceph_mon_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /ceph_mon/{ceph_mon_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_controller_fs_controller_fs_id() -> None:
    """PATCH /controller_fs/{controller_fs_id} without auth returns 401.

    Test Steps:
        - PATCH /controller_fs/{controller_fs_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /controller_fs/{controller_fs_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/controller_fs/{controller_fs_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /controller_fs/{controller_fs_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_devices_device_id() -> None:
    """PATCH /devices/{device_id} without auth returns 401.

    Test Steps:
        - PATCH /devices/{device_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /devices/{device_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/devices/{device_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /devices/{device_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_drbdconfig_drbdconfig_id() -> None:
    """PATCH /drbdconfig/{drbdconfig_id} without auth returns 401.

    Test Steps:
        - PATCH /drbdconfig/{drbdconfig_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /drbdconfig/{drbdconfig_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/drbdconfig/{drbdconfig_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /drbdconfig/{drbdconfig_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_event_suppression_event_suppression_uuid() -> None:
    """PATCH /event_suppression/{event_suppression_uuid} without auth returns 401.

    Test Steps:
        - PATCH /event_suppression/{event_suppression_uuid} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /event_suppression/{event_suppression_uuid} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/event_suppression/{event_suppression_uuid}")
    validate_equals(response.get_status_code(), 401, "PATCH /event_suppression/{event_suppression_uuid} without auth returns 401")


@mark.p1
def test_bad_auth_patch_iextoam_extoam_id() -> None:
    """PATCH /iextoam/{extoam_id} without auth returns 401.

    Test Steps:
        - PATCH /iextoam/{extoam_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /iextoam/{extoam_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/iextoam/{extoam_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /iextoam/{extoam_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_ihosts_host_id() -> None:
    """PATCH /ihosts/{host_id} without auth returns 401.

    Test Steps:
        - PATCH /ihosts/{host_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /ihosts/{host_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/ihosts/{host_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /ihosts/{host_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_iinterfaces_interface_id() -> None:
    """PATCH /iinterfaces/{interface_id} without auth returns 401.

    Test Steps:
        - PATCH /iinterfaces/{interface_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /iinterfaces/{interface_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/iinterfaces/{interface_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /iinterfaces/{interface_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_ilvgs_volumegroup_id() -> None:
    """PATCH /ilvgs/{volumegroup_id} without auth returns 401.

    Test Steps:
        - PATCH /ilvgs/{volumegroup_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /ilvgs/{volumegroup_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/ilvgs/{volumegroup_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /ilvgs/{volumegroup_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_imemorys_memory_id() -> None:
    """PATCH /imemorys/{memory_id} without auth returns 401.

    Test Steps:
        - PATCH /imemorys/{memory_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /imemorys/{memory_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/imemorys/{memory_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /imemorys/{memory_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_isensorgroups_sensorgroup_id() -> None:
    """PATCH /isensorgroups/{sensorgroup_id} without auth returns 401.

    Test Steps:
        - PATCH /isensorgroups/{sensorgroup_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /isensorgroups/{sensorgroup_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/isensorgroups/{sensorgroup_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /isensorgroups/{sensorgroup_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_isensors_sensor_id() -> None:
    """PATCH /isensors/{sensor_id} without auth returns 401.

    Test Steps:
        - PATCH /isensors/{sensor_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /isensors/{sensor_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/isensors/{sensor_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /isensors/{sensor_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_istors_stor_id() -> None:
    """PATCH /istors/{stor_id} without auth returns 401.

    Test Steps:
        - PATCH /istors/{stor_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /istors/{stor_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/istors/{stor_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /istors/{stor_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_remotelogging_remotelogging_id() -> None:
    """PATCH /remotelogging/{remotelogging_id} without auth returns 401.

    Test Steps:
        - PATCH /remotelogging/{remotelogging_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /remotelogging/{remotelogging_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/remotelogging/{remotelogging_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /remotelogging/{remotelogging_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_sdn_controller_controller_id() -> None:
    """PATCH /sdn_controller/{controller_id} without auth returns 401.

    Test Steps:
        - PATCH /sdn_controller/{controller_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /sdn_controller/{controller_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/sdn_controller/{controller_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /sdn_controller/{controller_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_service_parameter_parameter_id() -> None:
    """PATCH /service_parameter/{parameter_id} without auth returns 401.

    Test Steps:
        - PATCH /service_parameter/{parameter_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /service_parameter/{parameter_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/service_parameter/{parameter_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /service_parameter/{parameter_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_services_service_name() -> None:
    """PATCH /services/{service_name} without auth returns 401.

    Test Steps:
        - PATCH /services/{service_name} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /services/{service_name} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/services/{service_name}")
    validate_equals(response.get_status_code(), 401, "PATCH /services/{service_name} without auth returns 401")


@mark.p1
def test_bad_auth_patch_storage_ceph_storage_ceph_id() -> None:
    """PATCH /storage_ceph/{storage_ceph_id} without auth returns 401.

    Test Steps:
        - PATCH /storage_ceph/{storage_ceph_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /storage_ceph/{storage_ceph_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/storage_ceph/{storage_ceph_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /storage_ceph/{storage_ceph_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_storage_lvm_storage_lvm_id() -> None:
    """PATCH /storage_lvm/{storage_lvm_id} without auth returns 401.

    Test Steps:
        - PATCH /storage_lvm/{storage_lvm_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /storage_lvm/{storage_lvm_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/storage_lvm/{storage_lvm_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /storage_lvm/{storage_lvm_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_tpmconfig_tpmconfig_id() -> None:
    """PATCH /tpmconfig/{tpmconfig_id} without auth returns 401.

    Test Steps:
        - PATCH /tpmconfig/{tpmconfig_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /tpmconfig/{tpmconfig_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/tpmconfig/{tpmconfig_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /tpmconfig/{tpmconfig_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_idns_dns_id() -> None:
    """PATCH /idns/{dns_id} without auth returns 401.

    Test Steps:
        - PATCH /idns/{dns_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /idns/{dns_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/idns/{dns_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /idns/{dns_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_iinfra_infra_id() -> None:
    """PATCH /iinfra/{infra_id} without auth returns 401.

    Test Steps:
        - PATCH /iinfra/{infra_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /iinfra/{infra_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/iinfra/{infra_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /iinfra/{infra_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_intp_ntp_id() -> None:
    """PATCH /intp/{ntp_id} without auth returns 401.

    Test Steps:
        - PATCH /intp/{ntp_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /intp/{ntp_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/intp/{ntp_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /intp/{ntp_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_ipm_pm_id() -> None:
    """PATCH /ipm/{pm_id} without auth returns 401.

    Test Steps:
        - PATCH /ipm/{pm_id} without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /ipm/{pm_id} without auth")
    response = RestBadAuthKeywords().patch_without_auth("/ipm/{pm_id}")
    validate_equals(response.get_status_code(), 401, "PATCH /ipm/{pm_id} without auth returns 401")


@mark.p1
def test_bad_auth_patch_isystems() -> None:
    """PATCH /isystems without auth returns 401.

    Test Steps:
        - PATCH /isystems without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /isystems without auth")
    response = RestBadAuthKeywords().patch_without_auth("/isystems")
    validate_equals(response.get_status_code(), 401, "PATCH /isystems without auth returns 401")


@mark.p1
def test_bad_auth_patch_upgrade() -> None:
    """PATCH /upgrade without auth returns 401.

    Test Steps:
        - PATCH /upgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PATCH /upgrade without auth")
    response = RestBadAuthKeywords().patch_without_auth("/upgrade")
    validate_equals(response.get_status_code(), 401, "PATCH /upgrade without auth returns 401")


@mark.p1
def test_bad_auth_post_firewallrules_import_firewall_rules() -> None:
    """POST /firewallrules/import_firewall_rules without auth returns 401.

    Test Steps:
        - POST /firewallrules/import_firewall_rules without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /firewallrules/import_firewall_rules without auth")
    response = RestBadAuthKeywords().post_without_auth("/firewallrules/import_firewall_rules")
    validate_equals(response.get_status_code(), 401, "POST /firewallrules/import_firewall_rules without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_bulk_add() -> None:
    """POST /ihosts/bulk_add without auth returns 401.

    Test Steps:
        - POST /ihosts/bulk_add without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/bulk_add without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/bulk_add")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/bulk_add without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_host_id_addresses() -> None:
    """POST /ihosts/{host_id}/addresses without auth returns 401.

    Test Steps:
        - POST /ihosts/{host_id}/addresses without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/{host_id}/addresses without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/{host_id}/addresses")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/{host_id}/addresses without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_host_id_downgrade() -> None:
    """POST /ihosts/{host_id}/downgrade without auth returns 401.

    Test Steps:
        - POST /ihosts/{host_id}/downgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/{host_id}/downgrade without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/{host_id}/downgrade")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/{host_id}/downgrade without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_host_id_iinterfaces() -> None:
    """POST /ihosts/{host_id}/iinterfaces without auth returns 401.

    Test Steps:
        - POST /ihosts/{host_id}/iinterfaces without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/{host_id}/iinterfaces without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/{host_id}/iinterfaces")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/{host_id}/iinterfaces without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_host_id_istors() -> None:
    """POST /ihosts/{host_id}/istors without auth returns 401.

    Test Steps:
        - POST /ihosts/{host_id}/istors without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/{host_id}/istors without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/{host_id}/istors")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/{host_id}/istors without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_host_id_routes() -> None:
    """POST /ihosts/{host_id}/routes without auth returns 401.

    Test Steps:
        - POST /ihosts/{host_id}/routes without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/{host_id}/routes without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/{host_id}/routes")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/{host_id}/routes without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts_host_id_upgrade() -> None:
    """POST /ihosts/{host_id}/upgrade without auth returns 401.

    Test Steps:
        - POST /ihosts/{host_id}/upgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts/{host_id}/upgrade without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts/{host_id}/upgrade")
    validate_equals(response.get_status_code(), 401, "POST /ihosts/{host_id}/upgrade without auth returns 401")


@mark.p1
def test_bad_auth_post_addrpools() -> None:
    """POST /addrpools without auth returns 401.

    Test Steps:
        - POST /addrpools without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /addrpools without auth")
    response = RestBadAuthKeywords().post_without_auth("/addrpools")
    validate_equals(response.get_status_code(), 401, "POST /addrpools without auth returns 401")


@mark.p1
def test_bad_auth_post_ihosts() -> None:
    """POST /ihosts without auth returns 401.

    Test Steps:
        - POST /ihosts without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ihosts without auth")
    response = RestBadAuthKeywords().post_without_auth("/ihosts")
    validate_equals(response.get_status_code(), 401, "POST /ihosts without auth returns 401")


@mark.p1
def test_bad_auth_post_iinfra() -> None:
    """POST /iinfra without auth returns 401.

    Test Steps:
        - POST /iinfra without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /iinfra without auth")
    response = RestBadAuthKeywords().post_without_auth("/iinfra")
    validate_equals(response.get_status_code(), 401, "POST /iinfra without auth returns 401")


@mark.p1
def test_bad_auth_post_ilvgs() -> None:
    """POST /ilvgs without auth returns 401.

    Test Steps:
        - POST /ilvgs without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ilvgs without auth")
    response = RestBadAuthKeywords().post_without_auth("/ilvgs")
    validate_equals(response.get_status_code(), 401, "POST /ilvgs without auth returns 401")


@mark.p1
def test_bad_auth_post_ipvs() -> None:
    """POST /ipvs without auth returns 401.

    Test Steps:
        - POST /ipvs without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /ipvs without auth")
    response = RestBadAuthKeywords().post_without_auth("/ipvs")
    validate_equals(response.get_status_code(), 401, "POST /ipvs without auth returns 401")


@mark.p1
def test_bad_auth_post_loads_import_load() -> None:
    """POST /loads/import_load without auth returns 401.

    Test Steps:
        - POST /loads/import_load without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /loads/import_load without auth")
    response = RestBadAuthKeywords().post_without_auth("/loads/import_load")
    validate_equals(response.get_status_code(), 401, "POST /loads/import_load without auth returns 401")


@mark.p1
def test_bad_auth_post_sdn_controller() -> None:
    """POST /sdn_controller without auth returns 401.

    Test Steps:
        - POST /sdn_controller without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /sdn_controller without auth")
    response = RestBadAuthKeywords().post_without_auth("/sdn_controller")
    validate_equals(response.get_status_code(), 401, "POST /sdn_controller without auth returns 401")


@mark.p1
def test_bad_auth_post_service_parameter_apply() -> None:
    """POST /service_parameter/apply without auth returns 401.

    Test Steps:
        - POST /service_parameter/apply without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /service_parameter/apply without auth")
    response = RestBadAuthKeywords().post_without_auth("/service_parameter/apply")
    validate_equals(response.get_status_code(), 401, "POST /service_parameter/apply without auth returns 401")


@mark.p1
def test_bad_auth_post_service_parameter() -> None:
    """POST /service_parameter without auth returns 401.

    Test Steps:
        - POST /service_parameter without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /service_parameter without auth")
    response = RestBadAuthKeywords().post_without_auth("/service_parameter")
    validate_equals(response.get_status_code(), 401, "POST /service_parameter without auth returns 401")


@mark.p1
def test_bad_auth_post_storage_ceph() -> None:
    """POST /storage_ceph without auth returns 401.

    Test Steps:
        - POST /storage_ceph without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /storage_ceph without auth")
    response = RestBadAuthKeywords().post_without_auth("/storage_ceph")
    validate_equals(response.get_status_code(), 401, "POST /storage_ceph without auth returns 401")


@mark.p1
def test_bad_auth_post_tpmconfig() -> None:
    """POST /tpmconfig without auth returns 401.

    Test Steps:
        - POST /tpmconfig without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /tpmconfig without auth")
    response = RestBadAuthKeywords().post_without_auth("/tpmconfig")
    validate_equals(response.get_status_code(), 401, "POST /tpmconfig without auth returns 401")


@mark.p1
def test_bad_auth_post_upgrade() -> None:
    """POST /upgrade without auth returns 401.

    Test Steps:
        - POST /upgrade without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("POST /upgrade without auth")
    response = RestBadAuthKeywords().post_without_auth("/upgrade")
    validate_equals(response.get_status_code(), 401, "POST /upgrade without auth returns 401")


@mark.p1
def test_bad_auth_put_ihosts_host_id_state_host_cpus_modify() -> None:
    """PUT /ihosts/{host_id}/state/host_cpus_modify without auth returns 401.

    Test Steps:
        - PUT /ihosts/{host_id}/state/host_cpus_modify without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("PUT /ihosts/{host_id}/state/host_cpus_modify without auth")
    response = RestBadAuthKeywords().put_without_auth("/ihosts/{host_id}/state/host_cpus_modify")
    validate_equals(response.get_status_code(), 401, "PUT /ihosts/{host_id}/state/host_cpus_modify without auth returns 401")


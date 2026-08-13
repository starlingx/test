"""REST API GET resources with valid, invalid, and unauthenticated permutations."""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.bare_metal.disks.get_host_disks_keywords import GetHostDisksKeywords
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import GetHostsKeywords
from keywords.cloud_platform.rest.configuration.clusters.get_clusters_keywords import GetClustersKeywords
from keywords.cloud_platform.rest.configuration.lldp.get_lldp_keywords import GetLldpKeywords
from keywords.cloud_platform.rest.configuration.networks.get_networks_keywords import GetNetworksKeywords
from keywords.cloud_platform.rest.configuration.service_parameter.get_service_parameter_keywords import GetServiceParameterKeywords
from keywords.cloud_platform.rest.configuration.servicegroup.get_servicegroup_keywords import GetServicegroupKeywords
from keywords.cloud_platform.rest.configuration.servicenodes.get_servicenodes_keywords import GetServicenodesKeywords
from keywords.cloud_platform.rest.configuration.services.get_services_keywords import GetServicesKeywords
from keywords.cloud_platform.rest.fm.get_fm_keywords import GetFmKeywords
from keywords.cloud_platform.rest.configuration.addresses.get_host_addresses_keywords import GetHostAddressesKeywords

INVALID_UUID = "ffffffff-ffff-ffff-ffff-ffffffffffff"
INVALID_SHORT = "ffffffff"


@mark.p1
def test_get_networks_valid_auth() -> None:
    """Test GET /networks/{uuid} with valid auth returns 200.

    Test Steps:
        - Get networks list using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /networks with valid auth")
    output = GetNetworksKeywords().get_networks()
    validate_equals(output.get_networkobjects() is not None, True, "Networks list is valid")


@mark.p1
def test_get_networks_invalid_resource() -> None:
    """Test GET /networks/{invalid} with valid auth returns 404.

    Test Steps:
        - GET /networks with invalid UUID
        - Validate expected status code of 404
    """
    get_logger().log_test_case_step("GET /networks/{invalid} with valid auth")
    response = GetNetworksKeywords().get_networks_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 404, "GET /networks/{invalid} returns 404")


@mark.p2
def test_get_networks_no_auth() -> None:
    """Test GET /networks without auth returns 401.

    Test Steps:
        - GET /networks without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /networks without auth")
    response = GetNetworksKeywords().get_networks_no_auth()
    validate_equals(response.get_status_code(), 401, "GET /networks without auth returns 401")


@mark.p2
def test_get_clusters_valid_auth() -> None:
    """Test GET /clusters/{uuid} with valid auth returns 200.

    Test Steps:
        - Get clusters list using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /clusters with valid auth")
    output = GetClustersKeywords().get_clusters()
    validate_equals(output.get_clusterobjects() is not None, True, "Clusters list is valid")


@mark.p1
def test_get_clusters_invalid_resource() -> None:
    """Test GET /clusters/{invalid} with valid auth returns 400.

    Test Steps:
        - GET /clusters with invalid ID
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /clusters/{invalid} with valid auth")
    response = GetClustersKeywords().get_clusters_with_error(INVALID_SHORT)
    validate_equals(response.get_status_code(), 400, "GET /clusters/{invalid} returns 400")


@mark.p1
def test_get_clusters_no_auth() -> None:
    """Test GET /clusters without auth returns 401.

    Test Steps:
        - GET /clusters without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /clusters without auth")
    response = GetClustersKeywords().get_clusters_no_auth()
    validate_equals(response.get_status_code(), 401, "GET /clusters without auth returns 401")


@mark.p1
def test_get_alarms_valid_auth() -> None:
    """Test GET /alarms with valid auth returns 200.

    Test Steps:
        - Get alarms list using FM keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /alarms with valid auth")
    output = GetFmKeywords().get_alarms()
    validate_equals(output.get_alarm_objects() is not None, True, "Alarms list is valid")


@mark.p1
def test_get_alarms_invalid_resource() -> None:
    """Test GET /alarms/{invalid} with valid auth returns 404.

    Test Steps:
        - GET /alarms with invalid UUID
        - Validate expected status code of 404
    """
    get_logger().log_test_case_step("GET /alarms/{invalid} with valid auth")
    response = GetFmKeywords().get_alarms_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 404, "GET /alarms/{invalid} returns 404")


@mark.p2
def test_get_alarms_no_auth() -> None:
    """Test GET /alarms without auth returns 401.

    Test Steps:
        - GET /alarms without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /alarms without auth")
    response = GetFmKeywords().get_alarms_no_auth(INVALID_UUID)
    validate_equals(response.get_status_code(), 401, "GET /alarms without auth returns 401")


@mark.p1
def test_get_devices_valid_auth() -> None:
    """Test GET /ihosts/{uuid} with valid auth returns 200.

    Test Steps:
        - Get hosts using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /ihosts with valid auth")
    output = GetHostsKeywords().get_hosts()
    validate_equals(output.get_all_system_host_show_objects() is not None, True, "Hosts list is valid")


@mark.p1
def test_get_devices_invalid_resource() -> None:
    """Test GET /ihosts/host-invalid/pci_devices with valid auth returns 400.

    Test Steps:
        - GET /ihosts with invalid hostname
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /ihosts/host-invalid/pci_devices")
    response = GetHostAddressesKeywords().get_host_addresses_with_error("host-invalid")
    validate_equals(response.get_status_code(), 400, "GET /ihosts/{invalid}/addresses returns 400")


@mark.p1
def test_get_devices_not_found() -> None:
    """Test GET /ihosts/host-invalid returns 404.

    Test Steps:
        - GET /ihosts with non-existent host
        - Validate expected status code of 404
    """
    get_logger().log_test_case_step("GET /ihosts/host-invalid")
    response = GetHostsKeywords().get_host_with_error("host-invalid")
    validate_equals(response.get_status_code(), 404, "GET /ihosts/host-invalid returns 404")


@mark.p1
def test_get_devices_no_auth() -> None:
    """Test GET /ihosts without auth returns 401.

    Test Steps:
        - GET /ihosts without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /ihosts without auth")
    hosts = GetHostsKeywords().get_hosts()
    uuid = hosts.get_all_system_host_show_objects()[0].get_uuid()
    response = GetHostsKeywords().get_host_no_auth(uuid)
    validate_equals(response.get_status_code(), 401, "GET /ihosts without auth returns 401")


@mark.p1
def test_get_idisks_valid_auth() -> None:
    """Test GET /idisks/{uuid} with valid auth returns 200.

    Test Steps:
        - Get disks for each host using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /idisks with valid auth")
    hosts = GetHostsKeywords().get_hosts()
    for host in hosts.get_all_system_host_show_objects():
        output = GetHostDisksKeywords().get_disks(host.get_uuid())
        validate_equals(output is not None, True, f"Disks for host {host.get_uuid()} is valid")


@mark.p1
def test_get_lldp_agents_valid_auth() -> None:
    """Test GET /lldp_agents with valid auth returns 200.

    Test Steps:
        - Get LLDP agents using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /lldp_agents with valid auth")
    output = GetLldpKeywords().get_lldp_agents()
    validate_equals(output.get_lldp_agent_objects() is not None, True, "LLDP agents list is valid")


@mark.p1
def test_get_lldp_agents_invalid_resource() -> None:
    """Test GET /lldp_agents/{invalid} with valid auth returns 400.

    Test Steps:
        - GET /lldp_agents with invalid ID
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /lldp_agents/{invalid}")
    response = GetLldpKeywords().get_lldp_agents_with_error(INVALID_SHORT)
    validate_equals(response.get_status_code(), 400, "GET /lldp_agents/{invalid} returns 400")


@mark.p1
def test_get_lldp_agents_no_auth() -> None:
    """Test GET /lldp_agents without auth returns 401.

    Test Steps:
        - GET /lldp_agents without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /lldp_agents without auth")
    output = GetLldpKeywords().get_lldp_agents()
    agents = output.get_lldp_agent_objects()
    if agents:
        response = GetLldpKeywords().get_lldp_agents_no_auth(agents[0].get_uuid())
        validate_equals(response.get_status_code(), 401, "GET /lldp_agents without auth returns 401")


@mark.p1
@mark.lab_is_simplex
def test_get_lldp_neighbours_valid_auth() -> None:
    """Test GET /lldp_neighbours with valid auth returns 200.

    Test Steps:
        - Get LLDP neighbours using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /lldp_neighbours with valid auth")
    output = GetLldpKeywords().get_lldp_neighbours()
    validate_equals(output.get_lldp_neighbour_objects() is not None, True, "LLDP neighbours list is valid")


@mark.p1
@mark.lab_is_simplex
def test_get_lldp_neighbours_not_found() -> None:
    """Test GET /lldp_neighbours/{invalid} returns 404.

    Test Steps:
        - GET /lldp_neighbours with invalid UUID
        - Validate expected status code of 404
    """
    get_logger().log_test_case_step("GET /lldp_neighbours/{invalid}")
    response = GetLldpKeywords().get_lldp_neighbours_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 404, "GET /lldp_neighbours/{invalid} returns 404")


@mark.p1
@mark.lab_is_simplex
def test_get_lldp_neighbours_no_auth() -> None:
    """Test GET /lldp_neighbours without auth returns 401.

    Test Steps:
        - GET /lldp_neighbours without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /lldp_neighbours without auth")
    output = GetLldpKeywords().get_lldp_neighbours()
    neighbours = output.get_lldp_neighbour_objects()
    if neighbours:
        response = GetLldpKeywords().get_lldp_neighbours_no_auth(neighbours[0].get_uuid())
        validate_equals(response.get_status_code(), 401, "GET /lldp_neighbours without auth returns 401")


@mark.p1
def test_get_services_valid_auth() -> None:
    """Test GET /services with valid auth returns 200.

    Test Steps:
        - Get services using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /services with valid auth")
    output = GetServicesKeywords().get_services()
    validate_equals(output.get_serviceobjects() is not None, True, "Services list is valid")


@mark.p1
def test_get_services_invalid_resource() -> None:
    """Test GET /services/{invalid} with valid auth returns 400.

    Test Steps:
        - GET /services with invalid UUID
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /services/{invalid}")
    response = GetServicesKeywords().get_services_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 400, "GET /services/{invalid} returns 400")


@mark.p1
def test_get_services_no_auth() -> None:
    """Test GET /services without auth returns 401.

    Test Steps:
        - GET /services without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /services without auth")
    response = GetServicesKeywords().get_services_no_auth()
    validate_equals(response.get_status_code(), 401, "GET /services without auth returns 401")


@mark.p1
def test_get_servicenodes_valid_auth() -> None:
    """Test GET /servicenodes with valid auth returns 200.

    Test Steps:
        - Get servicenodes using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /servicenodes with valid auth")
    output = GetServicenodesKeywords().get_inodes()
    validate_equals(output.get_servicenodeobjects() is not None, True, "Servicenodes list is valid")


@mark.p1
def test_get_servicenodes_invalid_resource() -> None:
    """Test GET /servicenodes/{invalid} with valid auth returns 400.

    Test Steps:
        - GET /servicenodes with invalid UUID
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /servicenodes/{invalid}")
    response = GetServicenodesKeywords().get_inodes_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 400, "GET /servicenodes/{invalid} returns 400")


@mark.p1
def test_get_servicenodes_no_auth() -> None:
    """Test GET /servicenodes without auth returns 401.

    Test Steps:
        - GET /servicenodes without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /servicenodes without auth")
    response = GetServicenodesKeywords().get_inodes_no_auth()
    validate_equals(response.get_status_code(), 401, "GET /servicenodes without auth returns 401")


@mark.p1
def test_get_servicegroup_valid_auth() -> None:
    """Test GET /servicegroup with valid auth returns 200.

    Test Steps:
        - Get servicegroup using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /servicegroup with valid auth")
    output = GetServicegroupKeywords().get_sm_servicegroup()
    validate_equals(output.get_servicegroupobjects() is not None, True, "Servicegroup list is valid")


@mark.p1
def test_get_servicegroup_invalid_resource() -> None:
    """Test GET /servicegroup/{invalid} with valid auth returns 400.

    Test Steps:
        - GET /servicegroup with invalid UUID
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /servicegroup/{invalid}")
    response = GetServicegroupKeywords().get_sm_servicegroup_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 400, "GET /servicegroup/{invalid} returns 400")


@mark.p1
def test_get_servicegroup_no_auth() -> None:
    """Test GET /servicegroup without auth returns 401.

    Test Steps:
        - GET /servicegroup without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /servicegroup without auth")
    response = GetServicegroupKeywords().get_sm_servicegroup_no_auth()
    validate_equals(response.get_status_code(), 401, "GET /servicegroup without auth returns 401")


@mark.p2
def test_get_service_parameter_valid_auth() -> None:
    """Test GET /service_parameter with valid auth returns 200.

    Test Steps:
        - Get service parameters using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /service_parameter with valid auth")
    output = GetServiceParameterKeywords().get_parameters()
    validate_equals(output.get_serviceparameterobjects() is not None, True, "Service parameters list is valid")


@mark.p1
def test_get_service_parameter_invalid_resource() -> None:
    """Test GET /service_parameter/{invalid} with valid auth returns 400.

    Test Steps:
        - GET /service_parameter with invalid UUID
        - Validate expected status code of 400
    """
    get_logger().log_test_case_step("GET /service_parameter/{invalid}")
    response = GetServiceParameterKeywords().get_parameters_with_error(INVALID_UUID)
    validate_equals(response.get_status_code(), 400, "GET /service_parameter/{invalid} returns 400")


@mark.p1
def test_get_service_parameter_no_auth() -> None:
    """Test GET /service_parameter without auth returns 401.

    Test Steps:
        - GET /service_parameter without authentication
        - Validate expected status code of 401
    """
    get_logger().log_test_case_step("GET /service_parameter without auth")
    response = GetServiceParameterKeywords().get_parameters_no_auth()
    validate_equals(response.get_status_code(), 401, "GET /service_parameter without auth returns 401")

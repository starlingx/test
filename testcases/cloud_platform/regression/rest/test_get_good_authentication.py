"""REST API GET with valid authentication on sysinv endpoints."""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import GetHostsKeywords
from keywords.cloud_platform.rest.configuration.clusters.get_clusters_keywords import GetClustersKeywords
from keywords.cloud_platform.rest.configuration.networks.get_networks_keywords import GetNetworksKeywords
from keywords.cloud_platform.rest.configuration.service_parameter.get_service_parameter_keywords import GetServiceParameterKeywords
from keywords.cloud_platform.rest.configuration.servicegroup.get_servicegroup_keywords import GetServicegroupKeywords
from keywords.cloud_platform.rest.configuration.servicenodes.get_servicenodes_keywords import GetServicenodesKeywords
from keywords.cloud_platform.rest.configuration.services.get_services_keywords import GetServicesKeywords
from keywords.cloud_platform.rest.configuration.storage.get_storage_backends_keyword import GetStorageBackendKeywords
from keywords.cloud_platform.rest.configuration.system.get_system_keywords import GetSystemKeywords
from keywords.cloud_platform.rest.fm.get_fm_keywords import GetFmKeywords
from keywords.cloud_platform.rest.configuration.sysinv_endpoint_keywords import GetSysinvEndpointKeywords
from keywords.cloud_platform.rest.get_rest_url_keywords import GetRestUrlKeywords


def _get_sysinv_url() -> str:
    """Get the sysinv configuration URL.

    Returns:
        str: The configuration base URL.
    """
    return GetRestUrlKeywords().get_configuration_url()


@mark.p1
def test_get_addrpools() -> None:
    """Test GET /addrpools returns 200 with valid authentication.

    Test Steps:
        - GET /addrpools endpoint with valid authentication
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /addrpools")
    output = GetSysinvEndpointKeywords().get_addrpools()
    validate_equals(output is not None, True, "GET /addrpools returns valid response")


@mark.p1
def test_get_storage_backend() -> None:
    """Test GET /storage_backend returns 200 with valid authentication.

    Test Steps:
        - GET /storage_backend using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /storage_backend")
    output = GetStorageBackendKeywords().get_storage_backends()
    validate_equals(output is not None, True, "Storage backend output is valid")


@mark.p1
def test_get_storage_ceph() -> None:
    """Test GET /storage_ceph returns 200 with valid authentication.

    Test Steps:
        - GET /storage_ceph endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /storage_ceph")
    output = GetSysinvEndpointKeywords().get_storage_ceph()
    validate_equals(output is not None, True, "GET /storage_ceph returns valid response")


@mark.p1
def test_get_storage_lvm() -> None:
    """Test GET /storage_lvm returns 200 with valid authentication.

    Test Steps:
        - GET /storage_lvm endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /storage_lvm")
    output = GetSysinvEndpointKeywords().get_storage_lvm()
    validate_equals(output is not None, True, "GET /storage_lvm returns valid response")


@mark.p2
def test_get_ceph_mon() -> None:
    """Test GET /ceph_mon returns 200 with valid authentication.

    Test Steps:
        - GET /ceph_mon endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /ceph_mon")
    output = GetSysinvEndpointKeywords().get_ceph_mon()
    validate_equals(output is not None, True, "GET /ceph_mon returns valid response")


@mark.p2
def test_get_clusters() -> None:
    """Test GET /clusters returns 200 with valid authentication.

    Test Steps:
        - GET /clusters using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /clusters")
    output = GetClustersKeywords().get_clusters()
    validate_equals(output.get_clusterobjects() is not None, True, "Clusters output is valid")


@mark.p2
def test_get_controller_fs() -> None:
    """Test GET /controller_fs returns 200 with valid authentication.

    Test Steps:
        - GET /controller_fs endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /controller_fs")
    output = GetSysinvEndpointKeywords().get_controller_fs()
    validate_equals(output is not None, True, "GET /controller_fs returns valid response")


@mark.p2
def test_get_drbdconfig() -> None:
    """Test GET /drbdconfig returns 200 with valid authentication.

    Test Steps:
        - GET /drbdconfig endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /drbdconfig")
    output = GetSysinvEndpointKeywords().get_drbdconfig()
    validate_equals(output is not None, True, "GET /drbdconfig returns valid response")


@mark.p2
def test_get_health() -> None:
    """Test GET /health returns 200 with valid authentication.

    Test Steps:
        - GET /health endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /health")
    output = GetSysinvEndpointKeywords().get_health()
    validate_equals(output is not None, True, "GET /health returns valid response")


@mark.p2
def test_get_health_upgrade() -> None:
    """Test GET /health/upgrade returns 200 with valid authentication.

    Test Steps:
        - GET /health/upgrade endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /health/upgrade")
    output = GetSysinvEndpointKeywords().get_health_upgrade()
    validate_equals(output is not None, True, "GET /health/upgrade returns valid response")


@mark.p2
def test_get_idns() -> None:
    """Test GET /idns returns 200 with valid authentication.

    Test Steps:
        - GET /idns endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /idns")
    output = GetSysinvEndpointKeywords().get_idns()
    validate_equals(output is not None, True, "GET /idns returns valid response")


@mark.p2
def test_get_iextoam() -> None:
    """Test GET /iextoam returns 200 with valid authentication.

    Test Steps:
        - GET /iextoam endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /iextoam")
    output = GetSysinvEndpointKeywords().get_iextoam()
    validate_equals(output is not None, True, "GET /iextoam returns valid response")


@mark.p2
def test_get_ihosts() -> None:
    """Test GET /ihosts returns 200 with valid authentication.

    Test Steps:
        - GET /ihosts using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /ihosts")
    output = GetHostsKeywords().get_hosts()
    validate_equals(output.get_all_system_host_show_objects() is not None, True, "Hosts output is valid")


@mark.p2
def test_get_ihosts_bulk_export() -> None:
    """Test GET /ihosts/bulk_export returns 200 with valid authentication.

    Test Steps:
        - GET /ihosts/bulk_export endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /ihosts/bulk_export")
    output = GetSysinvEndpointKeywords().get_ihosts_bulk_export()
    validate_equals(output is not None, True, "GET /ihosts/bulk_export returns valid response")


@mark.p2
def test_get_intp() -> None:
    """Test GET /intp returns 200 with valid authentication.

    Test Steps:
        - GET /intp endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /intp")
    output = GetSysinvEndpointKeywords().get_intp()
    validate_equals(output is not None, True, "GET /intp returns valid response")


@mark.p2
def test_get_istors() -> None:
    """Test GET /istors returns 200 with valid authentication.

    Test Steps:
        - GET /istors endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /istors")
    output = GetSysinvEndpointKeywords().get_istors()
    validate_equals(output is not None, True, "GET /istors returns valid response")


@mark.p2
def test_get_isystems() -> None:
    """Test GET /isystems returns 200 with valid authentication.

    Test Steps:
        - GET /isystems using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /isystems")
    output = GetSystemKeywords().get_system()
    validate_equals(output.get_system_object() is not None, True, "System output is valid")


@mark.p2
def test_get_lldp_agents() -> None:
    """Test GET /lldp_agents returns 200 with valid authentication.

    Test Steps:
        - GET /lldp_agents endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /lldp_agents")
    output = GetSysinvEndpointKeywords().get_lldp_agents()
    validate_equals(output is not None, True, "GET /lldp_agents returns valid response")


@mark.p2
def test_get_lldp_neighbours() -> None:
    """Test GET /lldp_neighbours returns 200 with valid authentication.

    Test Steps:
        - GET /lldp_neighbours endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /lldp_neighbours")
    output = GetSysinvEndpointKeywords().get_lldp_neighbours()
    validate_equals(output is not None, True, "GET /lldp_neighbours returns valid response")


@mark.p2
def test_get_networks() -> None:
    """Test GET /networks returns 200 with valid authentication.

    Test Steps:
        - GET /networks using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /networks")
    output = GetNetworksKeywords().get_networks()
    validate_equals(output.get_networkobjects() is not None, True, "Networks output is valid")


@mark.p2
def test_get_remotelogging() -> None:
    """Test GET /remotelogging returns 200 with valid authentication.

    Test Steps:
        - GET /remotelogging endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /remotelogging")
    output = GetSysinvEndpointKeywords().get_remotelogging()
    validate_equals(output is not None, True, "GET /remotelogging returns valid response")


@mark.p2
def test_get_sdn_controller() -> None:
    """Test GET /sdn_controller returns 200 with valid authentication.

    Test Steps:
        - GET /sdn_controller endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET /sdn_controller")
    output = GetSysinvEndpointKeywords().get_sdn_controller()
    validate_equals(output is not None, True, "GET /sdn_controller returns valid response")


@mark.p2
def test_get_servicegroup() -> None:
    """Test GET /servicegroup returns 200 with valid authentication.

    Test Steps:
        - GET /servicegroup using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /servicegroup")
    output = GetServicegroupKeywords().get_sm_servicegroup()
    validate_equals(output.get_servicegroupobjects() is not None, True, "Servicegroup output is valid")


@mark.p2
def test_get_servicenodes() -> None:
    """Test GET /servicenodes returns 200 with valid authentication.

    Test Steps:
        - GET /servicenodes using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /servicenodes")
    output = GetServicenodesKeywords().get_inodes()
    validate_equals(output.get_servicenodeobjects() is not None, True, "Servicenodes output is valid")


@mark.p2
def test_get_service_parameter() -> None:
    """Test GET /service_parameter returns 200 with valid authentication.

    Test Steps:
        - GET /service_parameter using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /service_parameter")
    output = GetServiceParameterKeywords().get_parameters()
    validate_equals(output.get_serviceparameterobjects() is not None, True, "Service parameter output is valid")


@mark.p2
def test_get_services() -> None:
    """Test GET /services returns 200 with valid authentication.

    Test Steps:
        - GET /services using keyword
        - Validate output is not None
    """
    get_logger().log_test_case_step("GET /services")
    output = GetServicesKeywords().get_services()
    validate_equals(output.get_serviceobjects() is not None, True, "Services output is valid")


@mark.p2
def test_get_root() -> None:
    """Test GET / returns 200 with valid authentication.

    Test Steps:
        - GET / (API root) endpoint
        - Validate response is successful
    """
    get_logger().log_test_case_step("GET / (API root)")
    output = GetSysinvEndpointKeywords().get_root()
    validate_equals(output is not None, True, "GET / returns valid response")

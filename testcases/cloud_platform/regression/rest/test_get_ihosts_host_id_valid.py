"""REST API GET /ihosts/{uuid}/sub-resources with valid authentication."""

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.bare_metal.disks.get_host_disks_keywords import GetHostDisksKeywords
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import GetHostsKeywords
from keywords.cloud_platform.rest.bare_metal.lvgs.get_host_lvgs_keywords import GetHostLvgsKeywords
from keywords.cloud_platform.rest.bare_metal.memory.get_host_memory_keywords import GetHostMemoryKeywords
from keywords.cloud_platform.rest.bare_metal.pvs.get_host_pvs_keywords import GetHostPvsKeywords
from keywords.cloud_platform.rest.bare_metal.routes.get_host_routes_keywords import GetHostRoutesKeywords
from keywords.cloud_platform.rest.bare_metal.sensors.get_host_sensors_keywords import GetHostSensorsKeywords
from keywords.cloud_platform.rest.configuration.addresses.get_host_addresses_keywords import GetHostAddressesKeywords
from keywords.cloud_platform.rest.configuration.devices.system_host_device_keywords import GetHostDevicesKeywords
from keywords.cloud_platform.rest.configuration.storage.get_storage_keywords import GetStorageKeywords


@mark.p1
def test_get_host_addresses() -> None:
    """Test GET /ihosts/{uuid}/addresses returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get addresses for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/addresses")
        output = GetHostAddressesKeywords().get_host_addresses(host.get_uuid())
        validate_equals(output.get_host_address_objects() is not None, True, f"Host {host.get_uuid()} addresses list is valid")


@mark.p1
def test_get_host_idisks() -> None:
    """Test GET /ihosts/{uuid}/idisks returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get disks for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/idisks")
        output = GetHostDisksKeywords().get_disks(host.get_uuid())
        validate_equals(output is not None, True, f"Host {host.get_uuid()} disks output is valid")


@mark.p1
def test_get_host_ilvgs() -> None:
    """Test GET /ihosts/{uuid}/ilvgs returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get LVGs for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/ilvgs")
        output = GetHostLvgsKeywords().get_host_lvgs(host.get_uuid())
        validate_equals(output.get_lvg_objects() is not None, True, f"Host {host.get_uuid()} LVGs list is valid")


@mark.p1
def test_get_host_imemorys() -> None:
    """Test GET /ihosts/{uuid}/imemorys returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get memory for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/imemorys")
        output = GetHostMemoryKeywords().get_memory(host.get_uuid())
        validate_equals(output is not None, True, f"Host {host.get_uuid()} memory output is valid")


@mark.p1
def test_get_host_ipvs() -> None:
    """Test GET /ihosts/{uuid}/ipvs returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get physical volumes for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/ipvs")
        output = GetHostPvsKeywords().get_host_pvs(host.get_uuid())
        validate_equals(output.get_pv_objects() is not None, True, f"Host {host.get_uuid()} PVs list is valid")


@mark.p1
def test_get_host_isensors() -> None:
    """Test GET /ihosts/{uuid}/isensors returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get sensors for each host and validate response
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/isensors")
        output = GetHostSensorsKeywords().get_host_sensors(host.get_uuid())
        validate_equals(output.get_sensor_objects() is not None, True, f"Host {host.get_uuid()} sensors list is valid")


@mark.p1
def test_get_host_isensorgroups() -> None:
    """Test GET /ihosts/{uuid}/isensorgroups returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get sensor groups for each host and validate response
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/isensorgroups")
        output = GetHostSensorsKeywords().get_host_sensorgroups(host.get_uuid())
        validate_equals(output.get_sensorgroup_objects() is not None, True, f"Host {host.get_uuid()} sensorgroups list is valid")


@mark.p1
def test_get_host_istors() -> None:
    """Test GET /ihosts/{uuid}/istors returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get storage for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/istors")
        output = GetStorageKeywords().get_storage(host.get_uuid())
        validate_equals(output is not None, True, f"Host {host.get_uuid()} storage output is valid")


@mark.p1
def test_get_host_pci_devices() -> None:
    """Test GET /ihosts/{uuid}/pci_devices returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get PCI devices for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/pci_devices")
        output = GetHostDevicesKeywords().get_devices(host.get_uuid())
        validate_equals(output is not None, True, f"Host {host.get_uuid()} PCI devices output is valid")


@mark.p1
def test_get_host_routes() -> None:
    """Test GET /ihosts/{uuid}/routes returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get routes for each host and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}/routes")
        output = GetHostRoutesKeywords().get_host_routes(host.get_uuid())
        validate_equals(output.get_route_objects() is not None, True, f"Host {host.get_uuid()} routes list is valid")


@mark.p2
def test_get_host_show() -> None:
    """Test GET /ihosts/{uuid} returns 200.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Get host details and validate output
    """
    hosts_output = GetHostsKeywords().get_hosts()
    for host in hosts_output.get_all_system_host_show_objects():
        get_logger().log_test_case_step(f"GET /ihosts/{host.get_uuid()}")
        output = GetHostsKeywords().get_host(host.get_uuid())
        validate_equals(output.get_all_system_host_show_objects() is not None, True, f"Host {host.get_uuid()} show objects list is valid")

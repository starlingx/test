"""REST API GET /ihosts with invalid UUID formats."""

import string

from pytest import mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals
from keywords.cloud_platform.rest.bare_metal.hosts.get_hosts_keywords import GetHostsKeywords
from keywords.cloud_platform.rest.configuration.addresses.get_host_addresses_keywords import GetHostAddressesKeywords


@mark.p1
def test_get_ihosts_short_uuid_returns_400() -> None:
    """Test GET /ihosts/{short_uuid}/addresses returns 400.

    A truncated UUID is not a valid RFC 4122 UUID and should be rejected.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Truncate each UUID and request addresses
        - Validate expected status code of 400 is received
    """
    hosts_output = GetHostsKeywords().get_hosts()
    addresses_kw = GetHostAddressesKeywords()

    for host in hosts_output.get_all_system_host_show_objects():
        short_uuid = host.get_uuid()[:-1]
        get_logger().log_test_case_step(f"GET /ihosts/{short_uuid}/addresses (truncated UUID)")
        response = addresses_kw.get_host_addresses_with_error(short_uuid)
        validate_equals(response.get_status_code(), 400, f"GET /ihosts with short UUID '{short_uuid}' returns 400")


@mark.p1
def test_get_ihosts_invalid_uuid_returns_400() -> None:
    """Test GET /ihosts/{invalid_uuid}/addresses returns 400.

    A UUID with shifted characters is not valid and should be rejected.

    Test Steps:
        - Get all host UUIDs using ihost keyword
        - Shift characters to create invalid UUID and request addresses
        - Validate expected status code of 400 is received
    """
    hosts_output = GetHostsKeywords().get_hosts()
    addresses_kw = GetHostAddressesKeywords()

    for host in hosts_output.get_all_system_host_show_objects():
        uuid = host.get_uuid()
        shifted_uuid = "".join(chr((ord(c) - ord("a") + 6) % 26 + ord("a")) if c in string.ascii_lowercase else c for c in uuid.lower())
        get_logger().log_test_case_step(f"GET /ihosts/{shifted_uuid}/addresses (invalid UUID)")
        response = addresses_kw.get_host_addresses_with_error(shifted_uuid)
        validate_equals(response.get_status_code(), 400, f"GET /ihosts with invalid UUID '{shifted_uuid}' returns 400")

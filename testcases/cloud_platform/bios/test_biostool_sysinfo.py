from pytest import mark

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_not_none
from keywords.bmc.biostool.biostool_keywords import BiosToolKeywords


@mark.p3
@mark.lab_has_bmc_redfish
def test_biostool_sysinfo():
    """Smoke test: the biostool keyword can reach the BMC and read system info.

    Connects to controller-0's BMC (using the bm_ip/bm_username/bm_password
    from the lab config) over Redfish and runs the read-only sysinfo query.
    This is the most basic end-to-end check of the biostool keyword: it
    confirms the connection, authentication, and system-info read path all
    work, without touching any BIOS attribute or changing anything on the
    host.

    Test Steps:
      - Look up controller-0's BMC connection info from the lab config
      - Read system info from the BMC
      - Confirm a Manufacturer or Model is reported
    """
    node = ConfigurationManager.get_lab_config().get_node("controller-0")
    validate_not_none(node, "controller-0 exists in the lab config")
    validate_not_none(node.get_bm_ip(), "controller-0 has a bm_ip configured")

    bios_tool = BiosToolKeywords(node.get_bm_ip(), node.get_bm_username(), node.get_bm_password())
    system_info = bios_tool.sysinfo()

    get_logger().log_info(f"BMC sysinfo: Manufacturer='{system_info.get_manufacturer()}', Model='{system_info.get_model()}'")
    validate_not_none(system_info.get_manufacturer() or system_info.get_model(), "BMC reports a Manufacturer or Model")

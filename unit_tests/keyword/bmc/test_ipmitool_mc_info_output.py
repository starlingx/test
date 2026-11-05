from keywords.bmc.ipmitool.mc.info.object.ipmitool_mc_info_output import IPMIToolMcInfoOutput


def test_parses_mc_info_fields():
    """Read the BMC fields and ignore multi-line values and the shell prompt."""
    output = [
        "Device ID                 : 32\n",
        "Device Revision           : 1\n",
        "Firmware Revision         : 2.80\n",
        "IPMI Version              : 2.0\n",
        "Manufacturer ID           : 674\n",
        "Manufacturer Name         : DELL Inc\n",
        "Product ID                : 256 (0x0100)\n",
        "Product Name              : Unknown (0x100)\n",
        "Additional Device Support :\n",
        "    Sensor Device\n",
        "sysadmin@controller-0:~$ \n",
    ]
    mc_info = IPMIToolMcInfoOutput(output).get_ipmitool_mc_info_object()
    assert mc_info.get_firmware_revision() == "2.80"
    assert mc_info.get_ipmi_version() == "2.0"
    assert mc_info.get_manufacturer_name() == "DELL Inc"
    assert mc_info.get_product_id() == "256 (0x0100)"


def test_missing_fields_stay_none():
    """Leave fields unset when the BMC does not report them."""
    mc_info = IPMIToolMcInfoOutput("").get_ipmitool_mc_info_object()
    assert mc_info.get_firmware_revision() is None

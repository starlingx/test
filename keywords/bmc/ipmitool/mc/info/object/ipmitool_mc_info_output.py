from keywords.bmc.ipmitool.mc.info.object.ipmitool_mc_info_object import IPMIToolMcInfoObject


class IPMIToolMcInfoOutput:
    """Parses ``ipmitool mc info`` output.

    Fields are ``Name : Value`` lines. Lines without the `` : `` separator, such as
    continuation lines of multi-line fields and shell prompts, are ignored.
    """

    FIELD_SETTERS = {
        "Device ID": IPMIToolMcInfoObject.set_device_id,
        "Device Revision": IPMIToolMcInfoObject.set_device_revision,
        "Firmware Revision": IPMIToolMcInfoObject.set_firmware_revision,
        "IPMI Version": IPMIToolMcInfoObject.set_ipmi_version,
        "Manufacturer ID": IPMIToolMcInfoObject.set_manufacturer_id,
        "Manufacturer Name": IPMIToolMcInfoObject.set_manufacturer_name,
        "Product ID": IPMIToolMcInfoObject.set_product_id,
        "Product Name": IPMIToolMcInfoObject.set_product_name,
    }

    def __init__(self, ipmitool_output: str | list[str]):
        """Constructor.

        Args:
            ipmitool_output (str | list[str]): Raw ``ipmitool mc info`` output.
        """
        text = "".join(ipmitool_output) if isinstance(ipmitool_output, list) else ipmitool_output
        self.ipmitool_mc_info_object = IPMIToolMcInfoObject()
        for line in text.splitlines():
            if " : " not in line:
                continue
            name, value = line.split(" : ", 1)
            setter = self.FIELD_SETTERS.get(name.strip())
            if setter:
                setter(self.ipmitool_mc_info_object, value.strip())

    def get_ipmitool_mc_info_object(self) -> IPMIToolMcInfoObject:
        """Get the parsed BMC information.

        Returns:
            IPMIToolMcInfoObject: BMC identity and firmware.
        """
        return self.ipmitool_mc_info_object

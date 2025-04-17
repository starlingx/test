from keywords.bmc.ipmitool.chassis.status.object.ipmitool_chassis_status_object import IPMIToolChassisStatusObject
from keywords.bmc.ipmitool.ipmitool_table_parser import IPMIToolTableParser


class IPMIToolChassisStatusOutput:
    """
    IMPITool Chassis Status Output
    """

    def __init__(self, ipmitool_output):

        ipmitool_table_parser = IPMIToolTableParser(ipmitool_output)
        output_values = ipmitool_table_parser.get_output_values_list()
        self.ipmitool_chassis_status_object = IPMIToolChassisStatusObject()

        if "System Power" in output_values:
            self.ipmitool_chassis_status_object.set_system_power(output_values["System Power"])
        if "Power Overload" in output_values:
            self.ipmitool_chassis_status_object.set_power_overload(output_values["Power Overload"] == "true")  # this sets the string to True, or False
        if "Power Interlock" in output_values:
            self.ipmitool_chassis_status_object.set_power_interlock(output_values["Power Interlock"])
        if "Main Power Fault" in output_values:
            self.ipmitool_chassis_status_object.set_main_power_fault(output_values["Main Power Fault"] == "true")
        if "Power Control Fault" in output_values:
            self.ipmitool_chassis_status_object.set_power_control_fault(output_values["Power Control Fault"] == "true")
        if "Power Restore Policy" in output_values:
            self.ipmitool_chassis_status_object.set_power_restore_policy(output_values["Power Restore Policy"])
        if "Last Power Event" in output_values:
            self.ipmitool_chassis_status_object.set_last_power_event(output_values["Last Power Event"])
        if "Chassis Intrusion" in output_values:
            self.ipmitool_chassis_status_object.set_chassis_intrusion(output_values["Chassis Intrusion"])
        if "Front-Panel Lockout" in output_values:
            self.ipmitool_chassis_status_object.set_front_panel_lockout(output_values["Front-Panel Lockout"])
        if "Drive Fault" in output_values:
            self.ipmitool_chassis_status_object.set_drive_fault(output_values["Drive Fault"] == "true")
        if "Cooling/Fan Fault" in output_values:
            self.ipmitool_chassis_status_object.set_cooling_fan_fault(output_values["Cooling/Fan Fault"] == "true")
        if "Sleep Button Disable" in output_values:
            self.ipmitool_chassis_status_object.set_sleep_button_disable(output_values["Sleep Button Disable"])
        if "Diag Button Disable" in output_values:
            self.ipmitool_chassis_status_object.set_diag_button_disable(output_values["Diag Button Disable"])
        if "Reset Button Disable" in output_values:
            self.ipmitool_chassis_status_object.set_reset_button_disable(output_values["Reset Button Disable"])
        if "Power Button Disable" in output_values:
            self.ipmitool_chassis_status_object.set_power_button_disable(output_values["Power Button Disable"])
        if "Sleep Button Disabled" in output_values:
            self.ipmitool_chassis_status_object.set_sleep_button_disabled(output_values["Sleep Button Disabled"] == "true")
        if "Diag Button Disabled" in output_values:
            self.ipmitool_chassis_status_object.set_diag_button_disabled(output_values["Diag Button Disabled"] == "true")
        if "Reset Button Disabled" in output_values:
            self.ipmitool_chassis_status_object.set_reset_button_disabled(output_values["Reset Button Disabled"] == "true")
        if "Power Button Disabled" in output_values:
            self.ipmitool_chassis_status_object.set_power_button_disabled(output_values["Power Button Disabled"] == "true")

    def get_ipmitool_chassis_status_object(self) -> IPMIToolChassisStatusObject:
        """
        Getter for the ipmitool chassis status object

        Returns:
            IPMIToolChassisStatusObject: the IPMIToolChassisStatusObject

        """
        return self.ipmitool_chassis_status_object

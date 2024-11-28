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

        if output_values['System Power']:
            self.ipmitool_chassis_status_object.set_system_power(output_values['System Power'])
        if output_values['Power Overload']:
            self.ipmitool_chassis_status_object.set_power_overload(output_values['Power Overload'] == 'true')  # this sets the string to True, or False
        if output_values['Power Interlock']:
            self.ipmitool_chassis_status_object.set_power_interlock(output_values['Power Interlock'])
        if output_values['Main Power Fault']:
            self.ipmitool_chassis_status_object.set_main_power_fault(output_values['Main Power Fault'] == 'true')
        if output_values['Power Control Fault']:
            self.ipmitool_chassis_status_object.set_power_control_fault(output_values['Power Control Fault'] == 'true')
        if output_values['Power Restore Policy']:
            self.ipmitool_chassis_status_object.set_power_restore_policy(output_values['Power Restore Policy'])
        if output_values['Last Power Event']:
            self.ipmitool_chassis_status_object.set_last_power_event(output_values['Last Power Event'])
        if output_values['Chassis Intrusion']:
            self.ipmitool_chassis_status_object.set_chassis_intrusion(output_values['Chassis Intrusion'])
        if output_values['Front-Panel Lockout']:
            self.ipmitool_chassis_status_object.set_front_panel_lockout(output_values['Front-Panel Lockout'])
        if output_values['Drive Fault']:
            self.ipmitool_chassis_status_object.set_drive_fault(output_values['Drive Fault'] == 'true')
        if output_values['Cooling/Fan Fault']:
            self.ipmitool_chassis_status_object.set_cooling_fan_fault(output_values['Cooling/Fan Fault'] == 'true')
        if output_values['Sleep Button Disable']:
            self.ipmitool_chassis_status_object.set_sleep_button_disable(output_values['Sleep Button Disable'])
        if output_values['Diag Button Disable']:
            self.ipmitool_chassis_status_object.set_diag_button_disable(output_values['Diag Button Disable'])
        if output_values['Reset Button Disable']:
            self.ipmitool_chassis_status_object.set_reset_button_disable(output_values['Reset Button Disable'])
        if output_values['Power Button Disable']:
            self.ipmitool_chassis_status_object.set_power_button_disable(output_values['Power Button Disable'])
        if output_values['Sleep Button Disabled']:
            self.ipmitool_chassis_status_object.set_sleep_button_disabled(output_values['Sleep Button Disabled'] == 'true')
        if output_values['Diag Button Disabled']:
            self.ipmitool_chassis_status_object.set_diag_button_disabled(output_values['Diag Button Disabled'] == 'true')
        if output_values['Reset Button Disabled']:
            self.ipmitool_chassis_status_object.set_reset_button_disabled(output_values['Reset Button Disabled'] == 'true')
        if output_values['Power Button Disabled']:
            self.ipmitool_chassis_status_object.set_power_button_disabled(output_values['Power Button Disabled'] == 'true')

    def get_ipmitool_chassis_status_object(self) -> IPMIToolChassisStatusObject:
        """
        Getter for the ipmitool chassis status object
        Returns:

        """
        return self.ipmitool_chassis_status_object

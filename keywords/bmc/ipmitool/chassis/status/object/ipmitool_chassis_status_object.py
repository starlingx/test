class IPMIToolChassisStatusObject:
    """
    Class for IPMITool Chassis Status Object
    """

    def __init__(self):
        self.system_power: str = None
        self.power_overload: bool = None
        self.power_interlock: str = None
        self.main_power_fault: bool = None
        self.power_control_fault: bool = None
        self.power_restore_policy: str = None
        self.last_power_event: str = None
        self.chassis_intrusion: str = None
        self.front_panel_lockout: str = None
        self.drive_fault: bool = None
        self.cooling_fan_fault: bool = None
        self.sleep_button_disable: str = None
        self.diag_button_disable: str = None
        self.reset_button_disable: str = None
        self.power_button_disable: str = None
        self.sleep_button_disabled: bool = None
        self.diag_button_disabled: bool = None
        self.reset_button_disabled: bool = None
        self.power_button_disabled: bool = None

    def get_system_power(self) -> str:
        """
        Getter for system power
        Returns:

        """
        return self.system_power

    def set_system_power(self, system_power: str):
        """
        Setter for system power
        Args:
            system_power (): system power status

        Returns:

        """
        self.system_power = system_power

    def get_power_overload(self) -> bool:
        """
        Getter for power overload
        Returns:

        """
        return self.power_overload

    def set_power_overload(self, power_overload: bool):
        """
        Setter for power overload
        Args:
            power_overload (): the power over load value

        Returns:

        """
        self.power_overload = power_overload

    def get_power_interlock(self) -> str:
        """
        Getter for power interlock
        Returns:

        """
        return self.power_interlock

    def set_power_interlock(self, power_interlock: str):
        """
        Setter for power interlock
        Args:
            power_interlock (): the power interlock

        Returns:

        """
        self.power_interlock = power_interlock

    def get_main_power_fault(self) -> bool:
        """
        Getter for main power fault
        Returns:

        """
        return self.main_power_fault

    def set_main_power_fault(self, main_power_fault: bool):
        """
        Setter for main power fault
        Args:
            main_power_fault (): the main power fault

        Returns:

        """
        self.main_power_fault = main_power_fault

    def get_power_control_fault(self) -> bool:
        """
        Getter for power control fault
        Returns:

        """
        return self.power_control_fault

    def set_power_control_fault(self, power_control_fault: bool):
        """
        Setter power control fault
        Args:
            power_control_fault (): the power control fault

        Returns:

        """
        self.power_control_fault = power_control_fault

    def get_power_restore_policy(self) -> str:
        """
        Getter for power restore policy
        Returns:

        """
        return self.power_restore_policy

    def set_power_restore_policy(self, power_restore_policy: str):
        """
        Setter for power restore policy
        Args:
            power_restore_policy (): the power restore policy

        Returns:

        """
        self.power_restore_policy = power_restore_policy

    def get_last_power_event(self) -> str:
        """
        Getter for last power event
        Returns:

        """
        return self.last_power_event

    def set_last_power_event(self, last_power_event: str):
        """
        Setter for last power event
        Args:
            last_power_event (): the last power event

        Returns:

        """
        self.last_power_event = last_power_event

    def get_chassis_intrusion(self) -> str:
        """
        Getter for chassis intrusion
        Returns:

        """
        return self.chassis_intrusion

    def set_chassis_intrusion(self, chassis_intrusion: str):
        """
        Setter for chassis intrusion
        Args:
            chassis_intrusion (): the chassis intrusion

        Returns:

        """
        self.chassis_intrusion = chassis_intrusion

    def get_front_panel_lockout(self) -> str:
        """
        Getter for front panel lockout
        Returns:

        """
        return self.front_panel_lockout

    def set_front_panel_lockout(self, front_panel_lockout: str):
        """
        Setter for front panel lockout
        Args:
            front_panel_lockout (): the front panel lockout

        Returns:

        """
        self.front_panel_lockout = front_panel_lockout

    def get_drive_fault(self) -> bool:
        """
        Getter for drive fault
        Returns:

        """
        return self.drive_fault

    def set_drive_fault(self, drive_fault: bool):
        """
        Setter for drive fault
        Args:
            drive_fault (): the drive fault

        Returns:

        """
        self.drive_fault = drive_fault

    def get_cooling_fan_fault(self) -> bool:
        """
        Getter for cooling fan fault
        Returns:

        """
        return self.cooling_fan_fault

    def set_cooling_fan_fault(self, cooling_fan_fault: bool):
        """
        Setter for cooling fan fault
        Args:
            cooling_fan_fault (): the cooling fan fault

        Returns:

        """
        self.cooling_fan_fault = cooling_fan_fault

    def get_sleep_button_disable(self) -> str:
        """
        Getter for sleep button disable
        Returns:

        """
        return self.sleep_button_disable

    def set_sleep_button_disable(self, sleep_button_disable: str):
        """
        Setter for sleep button disable
        Args:
            sleep_button_disable (): the sleep button disable

        Returns:

        """
        self.sleep_button_disable = sleep_button_disable

    def get_diag_button_disable(self) -> str:
        """
        Getter for dial button disable
        Returns:

        """
        return self.diag_button_disable

    def set_diag_button_disable(self, diag_button_disable: str):
        """
        Setter for diag button disable
        Args:
            diag_button_disable (): the diag button disable

        Returns:

        """
        self.diag_button_disable = diag_button_disable

    def get_reset_button_disable(self) -> str:
        """
        Getter for reset button disable
        Returns:

        """
        return self.reset_button_disable

    def set_reset_button_disable(self, reset_button_disable: str):
        """
        Setter for reset button disable
        Args:
            reset_button_disable (): the reset button disable

        Returns:

        """
        self.reset_button_disable = reset_button_disable

    def get_power_button_disable(self) -> str:
        """
        Getter for power button disable
        Returns:

        """
        return self.power_button_disable

    def set_power_button_disable(self, power_button_disable: str):
        """
        Setter for power button disable
        Args:
            power_button_disable (): the power button disable

        Returns:

        """
        self.power_button_disable = power_button_disable

    def get_sleep_button_disabled(self) -> bool:
        """
        Getter for sleep button disabled
        Returns:

        """
        return self.sleep_button_disabled

    def set_sleep_button_disabled(self, sleep_button_disabled: bool):
        """
        Setter for sleep button disabled
        Args:
            sleep_button_disabled (): the sleep button disabled

        Returns:

        """
        self.sleep_button_disabled = sleep_button_disabled

    def get_diag_button_disabled(self) -> bool:
        """
        Getter for diag button disabled
        Returns:

        """
        return self.diag_button_disabled

    def set_diag_button_disabled(self, diag_button_disabled: bool):
        """
        Setter for diag button disabled
        Args:
            diag_button_disabled (): the diag button disabled

        Returns:

        """
        self.diag_button_disabled = diag_button_disabled

    def get_reset_button_disabled(self) -> bool:
        """
        Getter for reset button disabled
        Returns:

        """
        return self.reset_button_disabled

    def set_reset_button_disabled(self, reset_button_disabled: bool):
        """
        Setter for reset button disabled
        Args:
            reset_button_disabled (): the reset button disabled

        Returns:

        """
        self.reset_button_disabled = reset_button_disabled

    def get_power_button_disabled(self) -> bool:
        """
        Getter for power button disabled
        Returns:

        """
        return self.power_button_disabled

    def set_power_button_disabled(self, power_button_disabled: bool):
        """
        Setter for power button disabled
        Args:
            power_button_disabled (): the power button disabled

        Returns:

        """
        self.power_button_disabled = power_button_disabled

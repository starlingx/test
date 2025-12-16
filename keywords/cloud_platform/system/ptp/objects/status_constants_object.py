class StatusConstants:
    """Status and state constants for PTP operations."""

    def __init__(self):
        self.interface_down = "down"
        self.interface_up = "up"
        self.gnss_sma_disable = "disable"
        self.gnss_sma_enable = "enable"
        self.service_stop = "stop"
        self.service_start = "start"
        self.service_restart = "restart"
        self.alarm_set = "set"
        self.alarm_clear = "clear"
        self.phc_ctl_adj = "adj"
        self.phc_ctl_set = "set"

    def get_interface_down(self) -> str:
        """Get interface down status.

        Returns:
            str: The interface down status value.
        """
        return self.interface_down

    def get_interface_up(self) -> str:
        """Get interface up status.

        Returns:
            str: The interface up status value.
        """
        return self.interface_up

    def get_gnss_sma_disable(self) -> str:
        """Get GNSS/SMA disable status.

        Returns:
            str: The GNSS/SMA disable status value.
        """
        return self.gnss_sma_disable

    def get_gnss_sma_enable(self) -> str:
        """Get GNSS/SMA enable status.

        Returns:
            str: The GNSS/SMA enable status value.
        """
        return self.gnss_sma_enable

    def get_service_stop(self) -> str:
        """Get service stop status.

        Returns:
            str: The service stop status value.
        """
        return self.service_stop

    def get_service_start(self) -> str:
        """Get service start status.

        Returns:
            str: The service start status value.
        """
        return self.service_start

    def get_service_restart(self) -> str:
        """Get service restart status.

        Returns:
            str: The service restart status value.
        """
        return self.service_restart

    def get_alarm_set(self) -> str:
        """Get alarm set state.

        Returns:
            str: The alarm set state value.
        """
        return self.alarm_set

    def get_alarm_clear(self) -> str:
        """Get alarm clear state.

        Returns:
            str: The alarm clear state value.
        """
        return self.alarm_clear

    def get_phc_ctl_adj(self) -> str:
        """Get PHC control adj status.

        Returns:
            str: The PHC control adj status value.
        """
        return self.phc_ctl_adj

    def get_phc_ctl_set(self) -> str:
        """Get PHC control set status.

        Returns:
            str: The PHC control set status value.
        """
        return self.phc_ctl_set

class DcManagerAlarmSummaryObject:
    """
    Class that represents a row in the table shown in the output of the 'dcmanager alarm summary' command.
    """

    def __init__(self, subcloud_name):
        """
        Constructor

        Args:
            subcloud_name (str): the sublcloud name in the first column of the table shown in the output of the
            'dcmanager alarm summary' command.

        """
        self.subcloud_name: str = subcloud_name
        self.critical_alarms: int = -1
        self.major_alarms: int = -1
        self.minor_alarms: int = -1
        self.warnings: int = -1
        self.status: str = ""

    def set_subcloud_name(self, name: str):
        """
        Setter for the name
        """
        self.subcloud_name = name

    def get_subcloud_name(self) -> str:
        """
        Getter for the name
        """
        return self.subcloud_name

    def set_critical_alarms(self, critical_alarms: int):
        """
        Setter for the critical_alarms
        """
        self.critical_alarms = critical_alarms

    def get_critical_alarms(self) -> int:
        """
        Getter for the critical_alarms
        """
        return self.critical_alarms

    def set_major_alarms(self, major_alarms: int):
        """
        Setter for the major_alarms
        """
        self.major_alarms = major_alarms

    def get_major_alarms(self) -> int:
        """
        Getter for the major_alarms
        """
        return self.major_alarms

    def set_minor_alarms(self, minor_alarms: int):
        """
        Setter for the minor_alarms
        """
        self.minor_alarms = minor_alarms

    def get_minor_alarms(self) -> int:
        """
        Getter for the minor_alarms
        """
        return self.minor_alarms

    def set_warnings(self, warnings: int):
        """
        Setter for the warnings
        """
        self.warnings = warnings

    def get_warnings(self) -> int:
        """
        Getter for the warnings
        """
        return self.warnings

    def set_status(self, status: str):
        """
        Setter for the status
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for the status
        """
        return self.status

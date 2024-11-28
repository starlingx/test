class AlarmListObject:
    """
    Class to hold attributes of a alarm as returned by alarm list command
    """

    def __init__(
        self,
    ):
        self.alarm_id = None
        self.reason_text = None
        self.entity_id = None
        self.severity = None
        self.time_stamp = None

    def set_alarm_id(self, alarm_id: str):
        """
        Setter for alarm id
        Args:
            alarm_id (): the id of the alarm

        Returns:

        """
        self.alarm_id = alarm_id

    def get_alarm_id(self) -> str:
        """
        Getter for alarm id
        Returns: the alarm id

        """
        return self.alarm_id

    def set_reason_text(self, reason_text: str):
        """
        Setter for reason text
        Args:
            reason_text (): the reason text

        Returns:

        """
        self.reason_text = reason_text

    def get_reason_text(self) -> str:
        """
        Getter for reason text
        Returns: the reason text

        """
        return self.reason_text

    def set_entity_id(self, entity_id: str):
        """
        Setter for entity id
        Args:
            entity_id (): the entity id

        Returns:

        """
        self.entity_id = entity_id

    def get_entity_id(self) -> str:
        """
        Getter for entity_id
        Returns: the entity_id

        """
        return self.entity_id

    def set_severity(self, severity: str):
        """
        Setter for severity
        Args:
            severity (): the severity

        Returns:

        """
        self.severity = severity

    def get_severity(self) -> str:
        """
        Getter for severity
        Returns: the severity

        """
        return self.severity

    def set_time_stamp(self, time_stamp: str):
        """
        Setter for time stamp
        Args:
            time_stamp (): the time stamp

        Returns:

        """
        self.time_stamp = time_stamp

    def get_time_stamp(self) -> str:
        """
        Getter for time_stamp
        Returns: time_stamp

        """
        return self.time_stamp

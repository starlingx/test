class SystemHealthQueryObject:
    """
    This class represents a Health Query item as an object.
    This is typically a line in the system health-query* output table.
    """

    def __init__(self):
        self.check_name = None
        self.status = None
        self.reason = None

    def set_check_name(self, check_name: str) -> None:
        """
        Setter for the health check's name
        """
        self.check_name = check_name

    def get_check_name(self) -> str:
        """
        Getter for this health check's name
        """
        return self.check_name

    def set_status(self, status: str) -> None:
        """
        Setter for the health check's status
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for this health check's status
        """
        return self.status

    def set_reason(self, reason: str) -> None:
        """
        Setter for the health check's failure reason
        """
        self.reason = reason

    def get_reason(self) -> str:
        """
        Getter for this health check's failure reason
        """
        return self.reason

    def is_ok(self) -> bool:
        """
        Getter to check if the health check status is OK
        """
        return self.status is not None and "OK" in self.status

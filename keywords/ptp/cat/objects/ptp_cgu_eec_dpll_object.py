class PtpCguEecDpllObject:
    """
    Class for PTP CGU EEC_DPLL Object.
    """

    def __init__(self, current_reference: str, status: str):
        self.current_reference = current_reference
        self.status = status

    def get_current_reference(self) -> str:
        """
        Getter for current_reference.

        Returns:
            str: the current_reference.
        """
        return self.current_reference

    def set_current_reference(self, current_reference: str):
        """
        Setter for current_reference.

        Args:
            current_reference (str): the current_reference.

        """
        self.current_reference = current_reference

    def get_status(self) -> str:
        """
        Getter for status.

        Returns:
            str: the status.

        """
        return self.status

    def set_status(self, status: str):
        """
        Setter for status.

        Args:
            status (str): the status.

        """
        self.status = status

class PtpCguPpsDpllObject:
    """
    Class for PTP CGU PPS_DPLL Object.
    """

    def __init__(self, current_reference: str, status: str, phase_offset: str):
        self.current_reference = current_reference
        self.status = status
        self.phase_offset = phase_offset

    def get_current_reference(self) -> str:
        """
        Getter for current reference.

        Returns:
            str: the current reference.

        """
        return self.current_reference

    def set_current_reference(self, current_reference: str):
        """
        Setter for current reference.

        Args:
            current_reference (str): the current reference.

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

    def get_phase_offset(self) -> str:
        """
        Getter for phase offset.

        Returns:
            str: the phase offset.
        """
        return self.phase_offset

    def set_phase_offset(self, phase_offset: str):
        """
        Setter for phase offset.

        Args:
            phase_offset (str): the phase offset.

        """
        self.phase_offset = phase_offset

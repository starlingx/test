class FileSystemState:
    """
    Class for Controllerfs State
    """

    def __init__(self):
        self.status = None

    def set_status(self, status: str):
        """
        Setter for status
        Args:
            state:

        Returns:

        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for status
        Returns:

        """
        return self.status
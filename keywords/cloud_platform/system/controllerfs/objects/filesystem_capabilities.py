class FileSystemCapability:
    """
    Class for Controllerfs capabilities
    """

    def __init__(self):
        self.functions = None

    def set_functions(self, functions: []):
        """
        Setter for functions
        Args:
            state:

        Returns:

        """
        self.functions = functions

    def get_functions(self) -> str:
        """
        Getter functions
        Returns:

        """
        return self.functions
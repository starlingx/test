class SystemApplicationRemoveInput:
    """
    Class to support the parameters for 'system application-remove' command.
    An example of using this command is:

        'system application-remove -f hello-kitty'

    Where:
        -f: Forces the removal of the application, ignoring certain security or dependency checks. This can be useful if
         you want to remove the application quickly, even if it still has active components or dependencies.

         hello-kitty: the name of the application that you want to remove.

    """

    def __init__(self):
        """
        Constructor
        """
        self.app_name = None
        self.force_removal = False
        self.timeout_in_seconds = 60
        self.check_interval_in_seconds = 3

    def get_app_name(self) -> str:
        """
        Getter for this 'app_name' parameter.
        """
        return self.app_name

    def set_app_name(self, app_name: str):
        """
        Setter for the 'app_name' parameter.
        """
        self.app_name = app_name

    def get_force_removal(self) -> bool:
        """
        Getter for this 'force_removal' parameter.
        """
        return self.force_removal

    def set_force_removal(self, force_removal: bool):
        """
        Setter for the 'force_removal' parameter.
        """
        self.force_removal = force_removal

    def get_timeout_in_seconds(self) -> int:
        """
        Getter for this 'timeout_in_seconds' parameter.
        """
        return self.timeout_in_seconds

    def set_timeout_in_seconds(self, timeout_in_seconds: int):
        """
        Setter for the 'timeout_in_seconds' parameter.
        """
        self.timeout_in_seconds = timeout_in_seconds

    def set_check_interval_in_seconds(self, check_interval_in_seconds: int):
        """
        Setter for the 'check_interval_in_seconds' parameter.
        """
        self.check_interval_in_seconds = check_interval_in_seconds

    def get_check_interval_in_seconds(self) -> int:
        """
        Getter for this 'check_interval_in_seconds' parameter.
        """
        return self.check_interval_in_seconds

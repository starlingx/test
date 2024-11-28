class SystemApplicationApplyInput:
    """
    Class to support the parameters for 'system application-apply' command.
    An example of using this command is:

        'system application-upload -n hello-kitty'

    This class is able to generate this command just by previously setting the parameters.
    """

    def __init__(self):
        """
        Constructor
        """
        self.app_name = None
        self.timeout_in_seconds = 60
        self.check_interval_in_seconds = 3

    def set_app_name(self, app_name: str):
        """
        Setter for the 'app_name' parameter.
        """
        self.app_name = app_name

    def get_app_name(self) -> str:
        """
        Getter for this 'app_name' parameter.
        """
        return self.app_name

    def set_timeout_in_seconds(self, timeout_in_seconds: int):
        """
        Setter for the 'timeout_in_seconds' parameter.
        """
        self.timeout_in_seconds = timeout_in_seconds

    def get_timeout_in_seconds(self) -> int:
        """
        Getter for this 'timeout_in_seconds' parameter.
        """
        return self.timeout_in_seconds

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

class SystemApplicationUploadInput:
    """
    Class to support the parameters for 'system application-upload' command.
    An example of using this command is:

        'system application-upload -n hello-kitty-min-k8s-version.tgz -v 0.1.0 hello-kitty-min-k8s-version.tgz'

    This class is able to generate this command just by previously setting the parameters.
    """

    def __init__(self):
        """
        Constructor
        """
        self.app_name = None
        self.app_version = None
        self.automatic_installation = False
        self.tar_file_path = None
        self.force = False
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

    def set_app_version(self, app_version: str):
        """
        Setter for the 'app_version' parameter.
        """
        self.app_version = app_version

    def get_app_version(self) -> str:
        """
        Getter for this 'app_version' parameter.
        """
        return self.app_version

    def set_automatic_installation(self, automatic_installation: bool):
        """
        Setter for the 'automatic_installation' parameter.
        """
        self.automatic_installation = automatic_installation

    def get_automatic_installation(self) -> bool:
        """
        Getter for this 'automatic_installation' parameter.
        """
        return self.automatic_installation

    def set_tar_file_path(self, tar_file_path: str):
        """
        Setter for the 'tar_file_path' parameter.
        """
        self.tar_file_path = tar_file_path

    def get_tar_file_path(self) -> str:
        """
        Getter for this 'tar_file_path' parameter.
        """
        return self.tar_file_path

    def set_force(self, force: bool):
        """
        Setter for the 'force' parameter.
        """
        self.force = force

    def get_force(self) -> bool:
        """
        Getter for this 'force' parameter.
        """
        return self.force

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

class CustomInstaller:
    """
    Class to handle custom configuration object
    """

    def __init__(self, custom_dict: []):
        self.enabled_flag = custom_dict["enabled"]
        self.file_location = custom_dict["file_location"]
        self.file_name = custom_dict["file_name"]

    def get_enabled_flag(self) -> str:
        """
        Getter for custom enabled flag

        Returns: the enabled_flag

        """
        return self.enabled_flag

    def get_file_location(self) -> str:
        """
        Getter for helm file location

        Returns: the file_location

        """
        return self.file_location

    def get_file_name(self) -> str:
        """
        Getter for helm file name

        Returns: the file_name

        """
        return self.file_name

    def get_file_path(self) -> str:
        """
        This function will return a single string representation of the file path of custom object

        Returns: str

        """
        return f"{self.file_location}{self.file_name}"

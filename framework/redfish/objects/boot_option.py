class BootOption:
    """
    Class BootOption
    """

    def __init__(self, boot_option_id: str, name: str, display_name: str, boot_option_enabled: bool, description: str):
        self.boot_option_id = boot_option_id
        self.name = name
        self.display_name = display_name
        self.boot_option_enabled = boot_option_enabled
        self.description = description

    def get_boot_option_id(self) -> str:
        """
        Getter for boot option id

        Returns:
            str: the boot option id
        """
        return self.boot_option_id

    def set_boot_option_id(self, boot_option_id: str):
        """
        Setter for boot option id

        Args:
          boot_option_id (str): the boot option id

        Returns: None

        """
        self.boot_option_id = boot_option_id

    def get_name(self) -> str:
        """
        Getter for boot option name

        Returns:
            str: the boot option name

        """
        return self.name

    def set_name(self, name: str):
        """
        Setter for boot option name

        Args:
            name (str): the boot option name

        Returns: None

        """
        self.name = name

    def get_display_name(self) -> str:
        """
        Getter for boot option display name

        Returns:
            str: the boot option display name
        """
        return self.display_name

    def set_display_name(self, display_name: str):
        """
        Setter for boot option display name

        Args:
            display_name (str): the boot option display name

        Returns: None

        """
        self.display_name = display_name

    def get_boot_option_enabled(self) -> bool:
        """
        Getter for boot option enabled

        Returns:
            bool: boot option enabled
        """
        return self.boot_option_enabled

    def set_boot_option_enabled(self, boot_option_enabled: bool):
        """
        Setter for boot option enabled

        Args:
            boot_option_enabled (bool): boot option enabled

        Returns: None

        """
        self.boot_option_enabled = boot_option_enabled

    def get_description(self) -> str:
        """
        Getter for boot option description

        Returns:
            str: the boot option description
        """
        return self.description

    def set_description(self, description: str):
        """
        Setter for boot option description

        Args:
            description (str): the boot option description

        Returns: None

        """
        self.description = description

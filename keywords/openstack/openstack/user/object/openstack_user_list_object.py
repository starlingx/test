class OpenstackUserListObject:
    """
    Class to represent a single OpenStack user from the user list output.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.id = None
        self.name = None
        self.domain_id = None
        self.enabled = None

    def set_id(self, user_id: str):
        """Setter for user ID"""
        self.id = user_id

    def get_id(self) -> str:
        """Getter for user ID"""
        return self.id

    def set_name(self, name: str):
        """Setter for user name"""
        self.name = name

    def get_name(self) -> str:
        """Getter for user name"""
        return self.name

    def set_domain_id(self, domain_id: str):
        """Setter for domain ID"""
        self.domain_id = domain_id

    def get_domain_id(self) -> str:
        """Getter for domain ID"""
        return self.domain_id

    def set_enabled(self, enabled: str):
        """Setter for enabled status"""
        self.enabled = enabled

    def get_enabled(self) -> str:
        """Getter for enabled status"""
        return self.enabled

class OpenstackTokenIssueObject:
    """
    Class to represent an OpenStack token from the token issue output.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.id = None
        self.expires = None
        self.project_id = None
        self.user_id = None

    def set_id(self, token_id: str):
        """Setter for token ID"""
        self.id = token_id

    def get_id(self) -> str:
        """Getter for token ID"""
        return self.id

    def set_expires(self, expires: str):
        """Setter for expires"""
        self.expires = expires

    def get_expires(self) -> str:
        """Getter for expires"""
        return self.expires

    def set_project_id(self, project_id: str):
        """Setter for project ID"""
        self.project_id = project_id

    def get_project_id(self) -> str:
        """Getter for project ID"""
        return self.project_id

    def set_user_id(self, user_id: str):
        """Setter for user ID"""
        self.user_id = user_id

    def get_user_id(self) -> str:
        """Getter for user ID"""
        return self.user_id

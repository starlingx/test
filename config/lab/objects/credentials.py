class Credentials:
    """
    Class to handle credential objects
    """

    def __init__(self, credentials_dict: []):
        self.user_name = credentials_dict['user_name']
        self.password = credentials_dict['password']

    def get_user_name(self) -> str:
        """
        Getter for user name
        Returns: the user name

        """
        return self.user_name

    def get_password(self) -> str:
        """
        Getter for password
        Returns: the password

        """
        return self.password

    def to_string(self) -> str:
        """
        This function will return a single string representation of the Credentials object
        Returns: str

        """
        return f"{self.user_name} / {self.password}"

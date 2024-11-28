class SSHConnectionInfoClass:
    """
    This class represents all the information necessary to instantiate an SSH Connection.
    """

    def __init__(self, host: str, user: str, password: str):
        """
        Constructor
        Args:
            host: Hostname or IP Address
            user: Username of the user trying to establish the connection.
            password:  Password of the user establishing the connection.
        """

        self.host = host
        self.user = user
        self.password = password

    def get_host(self) -> str:
        """
        Getter for the host
        Returns (str): Hostname or IP Address.

        """
        return self.host

    def get_user(self) -> str:
        """
        Getter for the user
        Returns (str): Username of the user trying to establish the connection

        """
        return self.user

    def get_password(self) -> str:
        """
        Getter for the password
        Returns (str): Password of the user trying to establish the connection

        """
        return self.password

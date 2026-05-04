class DatabaseEntry:
    """Holds connection details for a single database.

    Args:
        host_name: the hostname of the database server
        db_name: the name of the database
        db_port: the port number
        user_name: the database user
        password: the database password
    """

    def __init__(self, host_name: str, db_name: str, db_port: int, user_name: str, password: str):
        """Initializes a DatabaseEntry with connection details.

        Args:
            host_name (str): The hostname of the database server.
            db_name (str): The name of the database.
            db_port (int): The port number.
            user_name (str): The database user.
            password (str): The database password.
        """
        self.host_name = host_name
        self.db_name = db_name
        self.db_port = db_port
        self.user_name = user_name
        self.password = password

    def __repr__(self) -> str:
        """Return string representation for debugging (password masked)."""
        return (
            f"DatabaseEntry(host_name='{self.get_host_name()}', db_name='{self.get_db_name()}', "
            f"db_port={self.get_db_port()}, user_name='{self.get_user_name()}', password='***')"
        )

    def get_host_name(self) -> str:
        """Getter for the host name of the db server.

        Returns:
            str: the host name
        """
        return self.host_name

    def get_db_name(self) -> str:
        """Getter for db name.

        Returns:
            str: the db name
        """
        return self.db_name

    def get_db_port(self) -> int:
        """Getter for db port.

        Returns:
            int: the db port
        """
        return self.db_port

    def get_user_name(self) -> str:
        """Getter for user name.

        Returns:
            str: the user name
        """
        return self.user_name

    def get_password(self) -> str:
        """Getter for password.

        Returns:
            str: the password
        """
        return self.password

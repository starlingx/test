import json5


class DatabaseConfig:
    """
    Class to hold configuration for database
    """

    def __init__(self, config):
        try:
            json_data = open(config)
        except FileNotFoundError:
            print(f"Could not find the database config file: {config}")
            raise

        database_dict = json5.load(json_data)
        self.host_name = database_dict['host_name']
        self.db_name = database_dict['db_name']
        self.db_port = database_dict['db_port']
        self.user_name = database_dict['user_name']
        self.password = database_dict['password']
        self.is_use_database = database_dict['use_database']

    def get_host_name(self) -> str:
        """
        Getter for the host name of the db server
        """
        return self.host_name

    def get_db_name(self) -> str:
        """
        Getter for db name
        Returns: the db name

        """
        return self.db_name

    def get_db_port(self) -> int:
        """
        Getter for db port
        Returns:

        """
        return self.db_port

    def get_user_name(self) -> str:
        """
        Getter for user name
        Returns: the user name

        """
        return self.user_name

    def get_password(self) -> str:
        """
        Getter for password
        Returns:

        """
        return self.password

    def use_database(self) -> bool:
        """
        Getter for use database value
        Returns:

        """
        return self.is_use_database

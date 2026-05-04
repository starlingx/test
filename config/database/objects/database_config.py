import json5

from config.database.objects.database_entry import DatabaseEntry


class DatabaseConfig:
    """Loads and manages multiple database configurations from a json5 file.

    Config format::

        {
          use_database: false,
          default_database: 'main',
          databases: {
            main: { host_name: '...', db_name: '...', db_port: 5432, user_name: '...', password: '...' },
            reporting: { ... },
          },
        }

    Use `get_database_entry(name)` to get a DatabaseEntry scoped to a
    specific database.
    """

    REQUIRED_ENTRY_FIELDS = {'host_name', 'db_name', 'db_port', 'user_name', 'password'}

    def __init__(self, config_file: str):
        """Initializes the DatabaseConfig by loading the specified config file.

        Args:
            config_file (str): Path to the database configuration file.

        Raises:
            FileNotFoundError: If the config file does not exist.
            ValueError: If the config is missing required sections or fields.
        """
        try:
            with open(config_file) as json_data:
                database_dict = json5.load(json_data)
        except FileNotFoundError:
            print(f"Could not find the database config file: {config_file}")
            raise

        self.is_use_database = database_dict['use_database']
        self.default_database_name = database_dict.get('default_database', 'default')

        databases = database_dict.get('databases')
        if not databases:
            raise ValueError(f"Database config '{config_file}' must contain a non-empty 'databases' section.")

        self.database_entries = {}
        for name, entry in databases.items():
            missing_fields = self.REQUIRED_ENTRY_FIELDS - set(entry.keys())
            if missing_fields:
                raise ValueError(f"Database entry '{name}' is missing required fields: {missing_fields}")
            self.database_entries[name] = DatabaseEntry(
                host_name=entry['host_name'],
                db_name=entry['db_name'],
                db_port=entry['db_port'],
                user_name=entry['user_name'],
                password=entry['password'],
            )

        if self.default_database_name not in self.database_entries:
            raise ValueError(
                f"default_database '{self.default_database_name}' not found in databases. "
                f"Available: {list(self.database_entries.keys())}"
            )

    def get_database_names(self) -> list[str]:
        """Returns the list of configured database names.

        Returns:
            list: the database names
        """
        return list(self.database_entries.keys())

    def get_default_database_name(self) -> str:
        """Returns the name of the default database.

        Returns:
            str: the default database name
        """
        return self.default_database_name

    def get_database_entry(self, database_name: str) -> DatabaseEntry:
        """Returns a DatabaseEntry for a specific database.

        Args:
            database_name: the name of the database entry

        Returns:
            DatabaseEntry: the connection details for the specified database

        Raises:
            KeyError: if the database name is not found in the config
        """
        if database_name not in self.database_entries:
            raise KeyError(f"Database '{database_name}' not found in config. Available databases: {list(self.database_entries.keys())}")
        return self.database_entries[database_name]

    def get_default_database_entry(self) -> DatabaseEntry:
        """Returns the DatabaseEntry for the default database.

        Returns:
            DatabaseEntry: the connection details for the default database
        """
        return self.database_entries[self.default_database_name]

    def use_database(self) -> bool:
        """Getter for use database value.

        Returns:
            bool: whether to use the database
        """
        return self.is_use_database

from typing import List

from keywords.cloud_platform.postgresql.object.psql_database_object import PsqlDatabaseObject


class PsqlListDatabasesOutput:
    """Parses the output of 'psql -l' command."""

    def __init__(self, psql_output: str) -> None:
        """Initialize PsqlListDatabasesOutput.

        Args:
            psql_output (str): Raw output from psql -l command.
        """
        self.databases: List[PsqlDatabaseObject] = []
        self._parse(psql_output)

    def _parse(self, output: str) -> None:
        """Parse psql -l output into database objects.

        Expected format is a table with | delimiters. Database name is in the first column.
        Continuation lines (starting with |) belong to the previous database entry.

        Args:
            output (str): Raw output string.
        """
        lines = output.split("\n") if isinstance(output, str) else output
        for line in lines:
            line = line.strip()
            if not line or line.startswith("-") or line.startswith("("):
                continue
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            name = parts[0]
            # Skip header line and continuation lines
            if name == "Name" or name == "":
                continue
            db = PsqlDatabaseObject()
            db.set_name(name)
            db.set_owner(parts[1])
            db.set_encoding(parts[2])
            self.databases.append(db)

    def get_databases(self) -> List[PsqlDatabaseObject]:
        """Get all parsed database objects.

        Returns:
            List[PsqlDatabaseObject]: List of database objects.
        """
        return self.databases

    def get_database_by_name(self, name: str) -> PsqlDatabaseObject:
        """Get a database object by name.

        Args:
            name (str): Database name.

        Returns:
            PsqlDatabaseObject: The matching database object.

        Raises:
            ValueError: If database not found.
        """
        for db in self.databases:
            if db.get_name() == name:
                return db
        raise ValueError(f"Database '{name}' not found in output")

    def is_database_present(self, name: str) -> bool:
        """Check if a database exists in the output.

        Args:
            name (str): Database name.

        Returns:
            bool: True if database exists.
        """
        return any(db.get_name() == name for db in self.databases)

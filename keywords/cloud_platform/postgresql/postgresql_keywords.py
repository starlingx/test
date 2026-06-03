from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from keywords.cloud_platform.postgresql.object.pg_is_ready_output import PgIsReadyOutput
from keywords.cloud_platform.postgresql.object.psql_list_databases_output import PsqlListDatabasesOutput
from keywords.cloud_platform.postgresql.object.psql_list_roles_output import PsqlListRolesOutput


class PostgresqlKeywords(BaseKeyword):
    """Keywords for PostgreSQL health and version checks."""

    def __init__(self, ssh_connection: SSHConnection) -> None:
        """Initialize PostgresqlKeywords.

        Args:
            ssh_connection (SSHConnection): SSH connection to the target host.
        """
        self.ssh_connection = ssh_connection

    def get_psql_version(self) -> str:
        """Get the installed psql client version string.

        Returns:
            str: Version output, e.g. "psql (PostgreSQL) 17.5 (Debian 17.5-1)".
        """
        output = self.ssh_connection.send("psql --version")
        self.validate_success_return_code(self.ssh_connection)
        for line in output:
            line = line.strip()
            if line.startswith("psql"):
                return line
        return ""

    def get_pg_isready(self) -> PgIsReadyOutput:
        """Run pg_isready as the postgres user and return parsed output.

        Returns:
            PgIsReadyOutput: Parsed pg_isready result with host, port, and status.
        """
        output = self.ssh_connection.send_as_sudo("sudo -u postgres pg_isready")
        self.validate_success_return_code(self.ssh_connection)
        return PgIsReadyOutput(output)

    def list_databases(self) -> PsqlListDatabasesOutput:
        """List all PostgreSQL databases via psql -l.

        Returns:
            PsqlListDatabasesOutput: Parsed database list.
        """
        output = self.ssh_connection.send_as_sudo("sudo -u postgres PAGER=cat psql -l")
        self.validate_success_return_code(self.ssh_connection)
        return PsqlListDatabasesOutput(output)

    def query_database(self, database: str, query: str) -> str:
        """Execute a SQL query against a specific database.

        Args:
            database (str): Database name to connect to.
            query (str): SQL query to execute.

        Returns:
            str: Raw query output.
        """
        output = self.ssh_connection.send_as_sudo(f'sudo -u postgres psql -d {database} -c "{query}"')
        self.validate_success_return_code(self.ssh_connection)
        if isinstance(output, list):
            return "\n".join(output)
        return output

    def list_roles(self) -> PsqlListRolesOutput:
        """List all PostgreSQL roles via psql \\du.

        Returns:
            PsqlListRolesOutput: Parsed role list.
        """
        output = self.ssh_connection.send_as_sudo('sudo -u postgres PAGER=cat psql -c "\\du"')
        self.validate_success_return_code(self.ssh_connection)
        return PsqlListRolesOutput(output)

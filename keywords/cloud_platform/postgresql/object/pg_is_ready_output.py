from typing import List

from keywords.cloud_platform.postgresql.object.pg_is_ready_object import PgIsReadyObject


class PgIsReadyOutput:
    """Parses the output of the 'pg_isready' command."""

    def __init__(self, pg_is_ready_output: List[str]) -> None:
        """Initialize PgIsReadyOutput.

        Args:
            pg_is_ready_output (List[str]): Raw output lines from pg_isready command.
        """
        self.pg_is_ready_object = PgIsReadyObject()
        self._parse(pg_is_ready_output)

    def _parse(self, output: List[str]) -> None:
        """Parse pg_isready output lines.

        Expected format: /var/run/postgresql:5432 - accepting connections

        Args:
            output (List[str]): Raw output lines.
        """
        for line in output:
            line = line.strip()
            if " - " in line:
                parts = line.split(" - ", 1)
                host_port = parts[0].strip()
                status = parts[1].strip()

                if ":" in host_port:
                    host, port = host_port.rsplit(":", 1)
                    self.pg_is_ready_object.set_host(host)
                    self.pg_is_ready_object.set_port(port)
                else:
                    self.pg_is_ready_object.set_host(host_port)

                self.pg_is_ready_object.set_status(status)
                break

    def get_pg_is_ready_object(self) -> PgIsReadyObject:
        """Get the parsed pg_isready object.

        Returns:
            PgIsReadyObject: Parsed connection readiness data.
        """
        return self.pg_is_ready_object

    def is_accepting_connections(self) -> bool:
        """Check if PostgreSQL is accepting connections.

        Returns:
            bool: True if status indicates accepting connections.
        """
        return self.pg_is_ready_object.is_accepting_connections()

from typing import List

from keywords.cloud_platform.postgresql.object.psql_role_object import PsqlRoleObject


class PsqlListRolesOutput:
    """Parses the output of 'psql -c \\du' command."""

    def __init__(self, psql_output: str) -> None:
        """Initialize PsqlListRolesOutput.

        Args:
            psql_output (str): Raw output from psql \\du command.
        """
        self.roles: List[PsqlRoleObject] = []
        self._parse(psql_output)

    def _parse(self, output: str) -> None:
        """Parse psql \\du output into role objects.

        Expected format:
         Role name | Attributes
        ----------------+------------------------------------------------------------
         admin-barbican |
         postgres       | Superuser, Create role, Create DB, Replication, Bypass RLS

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
            parts = [p.strip() for p in line.split("|", 1)]
            if len(parts) < 2:
                continue
            name = parts[0]
            # Skip header line
            if name == "Role name" or name == "":
                continue
            role = PsqlRoleObject()
            role.set_name(name)
            role.set_attributes(parts[1])
            self.roles.append(role)

    def get_roles(self) -> List[PsqlRoleObject]:
        """Get all parsed role objects.

        Returns:
            List[PsqlRoleObject]: List of role objects.
        """
        return self.roles

    def get_role_by_name(self, name: str) -> PsqlRoleObject:
        """Get a role object by name.

        Args:
            name (str): Role name.

        Returns:
            PsqlRoleObject: The matching role object.

        Raises:
            ValueError: If role not found.
        """
        for role in self.roles:
            if role.get_name() == name:
                return role
        raise ValueError(f"Role '{name}' not found in output")

    def is_role_present(self, name: str) -> bool:
        """Check if a role exists in the output.

        Args:
            name (str): Role name.

        Returns:
            bool: True if role exists.
        """
        return any(role.get_name() == name for role in self.roles)

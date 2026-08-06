from datetime import datetime, timezone
from typing import Optional


class IdGenerator:
    """Generates unique identifiers with a shared UTC timestamp.

    The timestamp is captured once at instantiation so that all
    identifiers produced by the same instance share it, making
    related resources easy to group together.

    The timestamp includes millisecond precision, making IDs
    naturally sortable by creation time when each resource uses
    its own IdGenerator instance.
    """

    def __init__(self):
        """Initialize and capture the current UTC timestamp with millisecond precision."""
        self.ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[:17]

    def generate(self, prefix: Optional[str] = None) -> str:
        """Generate a unique identifier.

        Args:
            prefix (Optional[str]): Optional prefix prepended to the identifier.

        Returns:
            str: Identifier in format "prefix-YYYYMMDDHHmmSSmmm" or
                "YYYYMMDDHHmmSSmmm" if no prefix provided.
        """
        if prefix:
            return f"{prefix}-{self.ts}"
        return self.ts

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4


class IdGenerator:
    """Generates unique identifiers with a shared UTC timestamp.

    The timestamp is captured once at instantiation so that all
    identifiers produced by the same instance share it, making
    related resources easy to group together.
    """

    def __init__(self):
        """Initialize and capture the current UTC timestamp."""
        self.ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    def generate(self, prefix: Optional[str] = None) -> str:
        """Generate a unique identifier.

        Args:
            prefix (Optional[str]): Optional prefix prepended to the identifier.

        Returns:
            str: Identifier in format "prefix-YYYYMMDDHHmmSS-xxxx" or
                "YYYYMMDDHHmmSS-xxxx" if no prefix provided.
        """
        tail = uuid4().hex[:4]
        if prefix:
            return f"{prefix}-{self.ts}-{tail}"
        return f"{self.ts}-{tail}"

import json
import re
from pathlib import Path
from typing import Any


class BiosExportArtifactWriter:
    """Writes redacted, deterministic JSON artifacts.

    Values that are not reported (``None``) are kept as JSON null, so the
    artifact distinguishes "not reported" from "reported as empty".

    This is deliberately not a keyword: BaseKeyword logs the arguments of every
    keyword call, which would put the unredacted payload in the test log.
    """

    SENSITIVE_KEY_PATTERN = re.compile(r"password|secret|token|communitystring", re.IGNORECASE)
    REDACTED_VALUE = "<redacted>"

    def redact(self, value: Any) -> Any:
        """Replace values of credential-like keys, recursively.

        Args:
            value (Any): JSON-compatible value.

        Returns:
            Any: Value with credential-like entries replaced by ``<redacted>``.
        """
        if isinstance(value, dict):
            return {key: self.REDACTED_VALUE if self.SENSITIVE_KEY_PATTERN.search(str(key)) else self.redact(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        return value

    def write_json(self, path: Path, value: Any) -> None:
        """Write a redacted JSON artifact with sorted keys.

        Args:
            path (Path): Destination file.
            value (Any): JSON-compatible value.
        """
        path.write_text(json.dumps(self.redact(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")

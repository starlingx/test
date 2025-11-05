from keywords.linux.lsmod.object.lsmod_object import LsmodObject
from framework.logging.automation_logger import get_logger
from typing import Dict, List
from framework.exceptions.keyword_exception import KeywordException


class LsmodOutput:
    """
    Parses raw `lsmod` output into LsmodModuleObject entries.
    """

    def __init__(self, lsmod_raw_output):

        if self.is_valid_output(lsmod_raw_output):
            parsed_list = self.parse_lines(lsmod_raw_output)
            self._modules: Dict[str, LsmodObject] = {}
            for entry in parsed_list:
                obj = LsmodObject()
                obj.set_name(entry["module"])
                obj.set_size(entry["size"])
                obj.set_used(entry["used"])
                obj.set_used_by_raw(",".join(entry["by"]))
                self._modules[entry["module"]] = obj
        else:
            raise KeywordException("The output header was not valid")

    def get_module(self, name: str) -> LsmodObject | None:
        """
        Return the lsmod object for the given kernel module name.

        Args:
            name (str):
                Name of the kernel module to look up.

        Returns:
            LsmodObject | None:
                The corresponding LsmodObject if the module is present in the
                parsed lsmod output, or None if the module is not loaded.
        """

        return self._modules.get(name)

    def has_module(self, name: str) -> bool:
        """
        Check whether a kernel module is present in the parsed lsmod output.

        Args:
            name (str):
                Name of the kernel module to check.

        Returns:
            bool:
                True if the module is loaded, False otherwise.
        """

        return name in self._modules

    def check_modules_loaded(self, modules: str) -> dict[str, bool]:
        """
        Check presence of the given module names inside the parsed output.

        Args:
            modules: iterable of module names to check

        Returns:
            dict[module_name, bool] — True when present, False otherwise.
        """

        result: dict[str, bool] = {}

        for module in modules:
            if module in self._modules:
                result[module] = True
            else:
                result[module] = False
        return result

    def is_valid_output(self, raw_output) -> bool:
        """
        Validate the raw lsmod output before parsing.

        Accepts either the raw string returned by the SSH wrapper or an iterable of lines.
        Returns True if the first non-empty line looks like an lsmod header.

        Expected tokens in header (case-insensitive): "module", "size", "used"
        """

        if isinstance(raw_output, str):
            lines = raw_output.splitlines()
        else:
            lines = list(raw_output)

        if not lines:
            return False

        header_line = None
        for raw in lines:
            line = (raw or "").strip()
            if line:
                header_line = line
                break

        if header_line is None:
            return False

        header_lower = header_line.lower()

        required_tokens = ("module", "size", "used")

        for token in required_tokens:
            if token not in header_lower:
                return False

        return True

    def parse_lines(self, lines: list[str]) -> list[dict]:
        """
        Parse lsmod lines into list of dicts:
            { "module": str, "size": int, "used": int, "by": list[str] }
        Args:
            lines (list[str]):
                Raw output lines returned from the `lsmod` command.
        Returns:
            list[dict]:
                A list of dictionaries representing parsed lsmod entries.
        """
        parsed: List[Dict] = []

        COLUMN_NAME = 0
        COLUMN_SIZE = 1
        COLUMN_USED = 2
        COLUMN_BY = 3
        MIN_REQUIRED_FIELDS = 3  # name, size, used
        MAX_SPLIT = COLUMN_BY  # split into up to 4 fields

        header_detected = False

        for raw_line in lines:
            # remove trailing characters from line
            line = (raw_line or "").strip()
            # Skip blank lines
            if not line:
                continue

            # Check if the line is the header of lsmod
            if not header_detected:
                lower = line.lower()
                if "module" in lower and "size" in lower:
                    header_detected = True
                    continue  # skip header row
                header_detected = True

            # parse the output in name, size, used, used_by_raw
            parts = line.split(None, MAX_SPLIT)

            if len(parts) < MIN_REQUIRED_FIELDS:
                get_logger().log_error(f"Skipping malformed lsmod line (too few fields): {line}")
                continue

            # Extract fields by index
            name = parts[COLUMN_NAME]
            size_str = parts[COLUMN_SIZE]
            used_str = parts[COLUMN_USED]
            by_raw = parts[COLUMN_BY] if len(parts) > COLUMN_BY else ""

            # convert size and used to integers
            try:
                size = int(size_str)
            except (ValueError, TypeError):
                get_logger().log_error(f"Invalid size for module '{name}': {size_str!r}; using 0")
                size = 0

            try:
                used = int(used_str)
            except (ValueError, TypeError):
                get_logger().log_error(f"Invalid used count for module '{name}': {used_str!r}; using 0")
                used = 0

            # Parse "Used by" list
            if by_raw:
                by_list = []
                for item in by_raw.split(","):
                    cleaned = item.strip()
                    if cleaned != "":
                        by_list.append(cleaned)
            else:
                by_list = []

            parsed.append(
                {
                    "module": name,
                    "size": size,
                    "used": used,
                    "by": by_list,
                }
            )
        return parsed

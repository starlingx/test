"""Parsed key=value pairs of one section of the nfv-vim config.ini."""

from typing import Dict, List, Union


class NfvVimConfigSectionOutput:
    """Parsed key=value pairs of one section of the nfv-vim config.ini.

    The input is the output of a command that prints the section header, its
    'key=value' lines, and the header of the next section (sed range print).
    Only the lines under the requested section header are kept.
    """

    def __init__(self, raw_output: Union[str, List[str]], section: str) -> None:
        """Parse the section.

        Args:
            raw_output (Union[str, List[str]]): Command output holding the section.
            section (str): Section name without brackets, e.g. 'instance-configuration'.
        """
        lines = raw_output.splitlines() if isinstance(raw_output, str) else raw_output
        self.section = section
        self.values: Dict[str, str] = {}
        in_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                in_section = stripped[1:-1] == section
                continue
            if not in_section or not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            self.values[key.strip()] = value.strip()

    def get_section(self) -> str:
        """Get the section name.

        Returns:
            str: Section name without brackets.
        """
        return self.section

    def has_key(self, key: str) -> bool:
        """Check whether the section sets a key.

        Args:
            key (str): Option name.

        Returns:
            bool: True if the key is present.
        """
        return key in self.values

    def get_value(self, key: str) -> str:
        """Get the value of a key.

        Args:
            key (str): Option name.

        Returns:
            str: The value as written in the file.

        Raises:
            ValueError: If the section does not set the key.
        """
        if key not in self.values:
            raise ValueError(f"nfv-vim config section [{self.section}] has no key '{key}'")
        return self.values[key]

    def get_keys(self) -> List[str]:
        """Get the keys set in the section.

        Returns:
            List[str]: Keys in file order.
        """
        return list(self.values)

    def __str__(self) -> str:
        """Return a short description.

        Returns:
            str: Section name and its values.
        """
        return f"NfvVimConfigSectionOutput([{self.section}] {self.values})"

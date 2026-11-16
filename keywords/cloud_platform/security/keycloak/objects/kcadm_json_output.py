"""Base Output for JSON returned by kcadm.sh and the Keycloak HTTP endpoints."""

import json
from typing import Any

from framework.exceptions.keyword_exception import KeywordException


class KcadmJsonOutput:
    """Parses a JSON body from command output, tolerating surrounding non-JSON text."""

    def __init__(self, output: str | list, description: str):
        """Constructor.

        kcadm returns clean JSON, but the surrounding shell can add warnings or
        echoed input before or after it, so the first position that decodes as
        a complete JSON value is used.

        Args:
            output (str | list): Raw command output.
            description (str): What is being parsed, for error messages.

        Raises:
            KeywordException: If no JSON body can be located or parsed.
        """
        text = "\n".join(output) if isinstance(output, list) else output
        decoder = json.JSONDecoder()
        for position, character in enumerate(text):
            if character not in "{[":
                continue
            try:
                self.json_data, _ = decoder.raw_decode(text, position)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise KeywordException(f"No JSON body found in {description}: {text[:300]}")
        self.description = description

    def get_json(self) -> Any:
        """Get the parsed JSON.

        Returns:
            Any: The parsed JSON (dict or list).
        """
        return self.json_data

    def get_json_list(self) -> list:
        """Get the parsed JSON, which must be a list.

        Returns:
            list: The parsed JSON list.

        Raises:
            KeywordException: If the parsed JSON is not a list.
        """
        if not isinstance(self.json_data, list):
            raise KeywordException(f"Expected a JSON list in {self.description}, got {type(self.json_data).__name__}")
        return self.json_data

    def get_json_dict(self) -> dict:
        """Get the parsed JSON, which must be an object.

        Returns:
            dict: The parsed JSON object.

        Raises:
            KeywordException: If the parsed JSON is not an object.
        """
        if not isinstance(self.json_data, dict):
            raise KeywordException(f"Expected a JSON object in {self.description}, got {type(self.json_data).__name__}")
        return self.json_data

    def get_description(self) -> str:
        """Get the description of what was parsed.

        Returns:
            str: The description.
        """
        return self.description

    def __str__(self) -> str:
        """Human-readable representation.

        Returns:
            str: The description of the parsed output.
        """
        return f"KcadmJsonOutput({self.description})"

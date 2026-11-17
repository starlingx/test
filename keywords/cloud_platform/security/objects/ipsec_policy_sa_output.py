"""Policy CHILD_SA evidence from swanctl --list-sas --raw.

The management-IPsec parser deliberately remains independent of this reader.
"""

import re

from keywords.cloud_platform.security.objects.ipsec_policy_child_sa import IPsecPolicyChildSA
from keywords.python.string import String


class IPsecPolicySAOutput:
    """Parse raw VICI messages without accepting empty or unrelated SA evidence."""

    def __init__(self, output: str | list[str]):
        """Parse established policy IKE associations and installed tunnel children.

        Args:
            output (str | list[str]): Checked swanctl --list-sas --raw output.
        """
        text = String.normalize_command_output(output)
        self.children = []
        remaining = text.strip()
        identities = set()
        while remaining:
            reply = re.match(r"list-sas reply\s*\{", remaining)
            if reply:
                fields, position = self._parse_fields(remaining, reply.end())
                if fields or remaining[position:].strip():
                    raise ValueError("Unexpected swanctl reply or output after completion")
                break
            match = re.match(r"list-sa event\s*\{", remaining)
            if not match:
                raise ValueError("Malformed swanctl policy SA response")
            message, position = self._parse_fields(remaining, match.end())
            remaining = remaining[position:].strip()
            for connection_name, ike in message.items():
                if not connection_name.startswith("k8s-node-"):
                    continue
                if not isinstance(ike, dict):
                    raise ValueError("Malformed policy IKE association")
                if ike.get("state") != "ESTABLISHED":
                    continue
                children = ike.get("child-sas", {})
                if not isinstance(children, dict):
                    raise ValueError("Malformed policy CHILD_SA collection")
                for child in children.values():
                    if not isinstance(child, dict):
                        raise ValueError("Malformed policy CHILD_SA")
                    if child.get("state") != "INSTALLED" or child.get("mode") != "TUNNEL":
                        continue
                    try:
                        association = IPsecPolicyChildSA(connection_name, ike, child)
                    except (KeyError, TypeError) as error:
                        raise ValueError("Incomplete policy CHILD_SA evidence") from error
                    if association.get_identity() in identities:
                        raise ValueError("Duplicate policy CHILD_SA identity")
                    identities.add(association.get_identity())
                    self.children.append(association)

    @classmethod
    def _parse_fields(cls, text: str, position: int) -> tuple[dict, int]:
        """Decode nested VICI fields while preserving selector brackets.

        Args:
            text (str): Raw VICI response.
            position (int): First character after an opening brace.

        Returns:
            tuple[dict, int]: Decoded fields and next unread character.
        """
        fields = {}
        while position < len(text):
            while position < len(text) and text[position].isspace():
                position += 1
            if position < len(text) and text[position] == "}":
                return fields, position + 1
            match = re.match(r"([^\s{}=\[\]]+)\s*([={])", text[position:])
            if not match or match[1] in fields:
                raise ValueError("Malformed or duplicate VICI field")
            key = match[1]
            position += match.end()
            if match[2] == "{":
                value, position = cls._parse_fields(text, position)
            elif position < len(text) and text[position] == "[":
                start, depth = position + 1, 1
                position += 1
                while position < len(text) and depth:
                    depth += (text[position] == "[") - (text[position] == "]")
                    position += 1
                if depth:
                    raise ValueError("Unterminated VICI list")
                value = text[start : position - 1].split()
            else:
                match = re.match(r"[^\s{}]+", text[position:])
                if not match:
                    raise ValueError("Missing VICI value")
                value = match[0]
                position += match.end()
            fields[key] = value
        raise ValueError("Unterminated VICI section")

    def get_installed_tunnels(self) -> list[IPsecPolicyChildSA]:
        """Return installed policy tunnels; an empty list is never proof of traffic.

        Returns:
            list[IPsecPolicyChildSA]: Observed policy CHILD_SAs.
        """
        return list(self.children)

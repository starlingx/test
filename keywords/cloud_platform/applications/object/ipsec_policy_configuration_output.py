"""Typed IPsec application evidence."""

import copy
import json

from framework.exceptions.keyword_exception import KeywordException


class IPsecPolicyConfigurationOutput:
    """Decode legacy generated configuration or JSON connection arrays."""

    def __init__(self, content: str):
        """Parse a checked ConfigMap response.

        Args:
            content (str): Kubernetes ConfigMap JSON.
        """
        configmap = json.loads(content)
        data = configmap.get("data", {})
        if "connections" in data and "local_conn" in data:
            decoded = {key: json.loads(data[key]) for key in ("connections", "local_conn")}
            if any(not isinstance(value, list) for value in decoded.values()):
                raise KeywordException("Invalid policy ConfigMap connection arrays")
            self.values = decoded
            return
        if isinstance(data.get("k8s-nodes.conf"), str) and data["k8s-nodes.conf"].strip():
            self.values = {"k8s-nodes.conf": data["k8s-nodes.conf"]}
            return
        raise KeywordException("Missing per-node policy configuration")

    def get_connections(self) -> list:
        """Return decoded connection records.

        Returns:
            list: Connections for JSON-format agents.
        """
        return copy.deepcopy(self.values.get("connections", []))

    def get_local_connections(self) -> list:
        """Return local bypass connection records.

        Returns:
            list: Local connection records.
        """
        return copy.deepcopy(self.values.get("local_conn", []))

    def get_configuration_text(self) -> str | None:
        """Return legacy generated configuration when present.

        Returns:
            str | None: Legacy configuration, or absent for JSON format.
        """
        return self.values.get("k8s-nodes.conf")

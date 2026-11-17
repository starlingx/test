"""Output object for 'kubectl get gatewayclass <name> --ignore-not-found -o yaml'."""

import yaml

from keywords.k8s.gateway.object.gateway_condition_object import GatewayConditionObject


class KubectlGetGatewayClassOutput:
    """Parsed output from 'kubectl get gatewayclass <name> --ignore-not-found -o yaml'.

    The GatewayClass is created by the Calico operator after the GatewayAPI CR is
    applied, so an empty output (class not created yet) is a valid reading.
    """

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw GatewayClass YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output; empty when the class does not exist.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = yaml.safe_load(content) if content and content.strip() else None
        self.present = bool(data)
        status = (data or {}).get("status") or {}
        self.conditions = GatewayConditionObject.build_condition_objects_from_dicts(status.get("conditions") or [])

    def is_present(self) -> bool:
        """Check whether the GatewayClass exists.

        Returns:
            bool: True if the GatewayClass exists, False otherwise.
        """
        return self.present

    def is_accepted(self) -> bool:
        """Check whether the GatewayClass reports Accepted=True.

        Returns:
            bool: True if the class exists and its Accepted condition is True, False otherwise.
        """
        return any(condition.get_condition_type() == "Accepted" and condition.is_true() for condition in self.conditions)

    def __str__(self) -> str:
        """Human-readable representation of the GatewayClass status.

        Returns:
            str: Whether the class exists and its conditions.
        """
        return f"KubectlGetGatewayClassOutput(present={self.present}, conditions={[str(condition) for condition in self.conditions]})"

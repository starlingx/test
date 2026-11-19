"""Output object for 'kubectl get httproute <name> -o yaml'."""

import yaml

from keywords.k8s.gateway.object.gateway_condition_object import GatewayConditionObject


class KubectlGetHTTPRouteOutput:
    """Parsed output from 'kubectl get httproute <name> -o yaml'."""

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw HTTPRoute YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = yaml.safe_load(content) or {}
        status = data.get("status") or {}
        self.parent_conditions: dict[str, list[GatewayConditionObject]] = {(parent.get("parentRef") or {}).get("name"): GatewayConditionObject.build_condition_objects_from_dicts(parent.get("conditions") or []) for parent in status.get("parents") or []}

    def is_accepted_by(self, gateway_name: str) -> bool:
        """Check whether a parent Gateway reports the route as Accepted=True.

        Args:
            gateway_name (str): The parent Gateway name.

        Returns:
            bool: True if the parent's Accepted condition is True, False otherwise.
        """
        return any(condition.get_condition_type() == "Accepted" and condition.is_true() for condition in self.parent_conditions.get(gateway_name, []))

    def __str__(self) -> str:
        """Human-readable representation of the HTTPRoute status.

        Returns:
            str: The conditions reported by each parent Gateway.
        """
        parents = {name: [str(condition) for condition in conditions] for name, conditions in self.parent_conditions.items()}
        return f"KubectlGetHTTPRouteOutput(parents={parents})"

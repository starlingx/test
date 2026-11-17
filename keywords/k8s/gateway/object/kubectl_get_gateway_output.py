"""Output object for 'kubectl get gateway <name> -o yaml'."""

import yaml

from keywords.k8s.gateway.object.gateway_condition_object import GatewayConditionObject


class KubectlGetGatewayOutput:
    """Parsed output from 'kubectl get gateway <name> -o yaml'."""

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw Gateway YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = yaml.safe_load(content) or {}
        status = data.get("status") or {}
        self.conditions = GatewayConditionObject.build_condition_objects_from_dicts(status.get("conditions") or [])
        self.listener_conditions: dict[str, list[GatewayConditionObject]] = {listener["name"]: GatewayConditionObject.build_condition_objects_from_dicts(listener.get("conditions") or []) for listener in status.get("listeners") or [] if listener.get("name")}

    def get_conditions(self) -> list[GatewayConditionObject]:
        """Get the top-level Gateway conditions.

        Returns:
            list[GatewayConditionObject]: The status.conditions entries.
        """
        return self.conditions

    def is_accepted(self) -> bool:
        """Check whether the Gateway reports Accepted=True.

        Returns:
            bool: True if the Accepted condition is True, False otherwise.
        """
        return any(condition.get_condition_type() == "Accepted" and condition.is_true() for condition in self.conditions)

    def is_listener_programmed(self, listener_name: str) -> bool:
        """Check whether a listener reports Programmed=True.

        Without a LoadBalancer controller the top-level Gateway stays Programmed=False
        (AddressNotAssigned) while its listeners are programmed, so the listener
        condition is the one that shows the dataplane is ready.

        Args:
            listener_name (str): The listener name from the Gateway spec.

        Returns:
            bool: True if the listener's Programmed condition is True, False otherwise.
        """
        return any(condition.get_condition_type() == "Programmed" and condition.is_true() for condition in self.listener_conditions.get(listener_name, []))

    def __str__(self) -> str:
        """Human-readable representation of the Gateway status.

        Returns:
            str: The top-level and listener conditions.
        """
        listeners = {name: [str(condition) for condition in conditions] for name, conditions in self.listener_conditions.items()}
        return f"KubectlGetGatewayOutput(conditions={[str(condition) for condition in self.conditions]}, listeners={listeners})"

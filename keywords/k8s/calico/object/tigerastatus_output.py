"""Output object for 'kubectl get tigerastatus calico -o yaml'."""

import yaml

from keywords.k8s.calico.object.tigerastatus_condition_object import TigeraStatusConditionObject


class TigeraStatusOutput:
    """Parsed output from 'kubectl get tigerastatus calico -o yaml'.

    The conditions are read from status.conditions[] by type, so the parsing does
    not depend on the 'kubectl describe' text layout.
    """

    def __init__(self, raw_output: str | list[str]):
        """Parse the raw TigeraStatus YAML output.

        Args:
            raw_output (str | list[str]): Raw SSH command output.
        """
        content = "".join(raw_output) if isinstance(raw_output, list) else raw_output
        data = yaml.safe_load(content) or {}
        status = data.get("status") or {}
        self.conditions: list[TigeraStatusConditionObject] = [self.build_condition_object_from_dict(condition) for condition in status.get("conditions") or []]

    @staticmethod
    def build_condition_object_from_dict(condition_dict: dict) -> TigeraStatusConditionObject:
        """Build a condition object from one status.conditions entry.

        Args:
            condition_dict (dict): One parsed status.conditions entry.

        Returns:
            TigeraStatusConditionObject: The condition.

        Raises:
            ValueError: If the entry has no type or no status.
        """
        condition_type = condition_dict.get("type")
        status = condition_dict.get("status")
        if not condition_type or not status:
            raise ValueError(f"TigeraStatus condition is missing its type or status: {condition_dict}")
        return TigeraStatusConditionObject(condition_type, status, condition_dict.get("reason"), condition_dict.get("message"))

    def get_conditions(self) -> list[TigeraStatusConditionObject]:
        """Get all conditions.

        Returns:
            list[TigeraStatusConditionObject]: The conditions in the order the operator reported them.
        """
        return self.conditions

    def has_condition(self, condition_type: str) -> bool:
        """Check whether a condition of the given type is reported.

        Args:
            condition_type (str): The condition type (e.g. 'Available').

        Returns:
            bool: True if the condition is reported, False otherwise.
        """
        return any(condition.get_condition_type() == condition_type for condition in self.conditions)

    def get_condition(self, condition_type: str) -> TigeraStatusConditionObject:
        """Get the condition of the given type.

        Args:
            condition_type (str): The condition type (e.g. 'Available').

        Returns:
            TigeraStatusConditionObject: The condition.

        Raises:
            ValueError: If the condition is not reported.
        """
        for condition in self.conditions:
            if condition.get_condition_type() == condition_type:
                return condition
        raise ValueError(f"TigeraStatus has no '{condition_type}' condition; reported: {[str(condition) for condition in self.conditions]}")

    def is_available(self) -> bool:
        """Check whether the Available condition is True.

        Returns:
            bool: True if Available is reported and True, False otherwise.
        """
        return self.has_condition("Available") and self.get_condition("Available").is_true()

    def is_degraded(self) -> bool:
        """Check whether the Degraded condition is True.

        Returns:
            bool: True if Degraded is reported and True, False otherwise.
        """
        return self.has_condition("Degraded") and self.get_condition("Degraded").is_true()

    def is_progressing(self) -> bool:
        """Check whether the Progressing condition is True.

        Returns:
            bool: True if Progressing is reported and True, False otherwise.
        """
        return self.has_condition("Progressing") and self.get_condition("Progressing").is_true()

    def get_unhealthy_conditions(self) -> list[str]:
        """Get the conditions that differ from a healthy operator.

        A healthy operator reports Available=True, Degraded=False and Progressing=False.

        Returns:
            list[str]: One entry per condition that is missing or differs from the healthy value; empty when healthy.
        """
        expected_statuses = {"Available": "True", "Degraded": "False", "Progressing": "False"}
        unhealthy = []
        for condition_type, expected_status in expected_statuses.items():
            if not self.has_condition(condition_type):
                unhealthy.append(f"{condition_type} not reported")
            elif self.get_condition(condition_type).get_status() != expected_status:
                unhealthy.append(str(self.get_condition(condition_type)))
        return unhealthy

    def __str__(self) -> str:
        """Human-readable representation of the TigeraStatus conditions.

        Returns:
            str: The reported conditions.
        """
        return f"TigeraStatusOutput(conditions={[str(condition) for condition in self.conditions]})"

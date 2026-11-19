"""Object for one status condition of a Gateway API resource."""

from typing import Optional


class GatewayConditionObject:
    """One status condition of a Gateway, GatewayClass or HTTPRoute."""

    def __init__(self, condition_type: str, status: str, reason: Optional[str], message: Optional[str]):
        """Initialize the condition.

        Args:
            condition_type (str): The condition type (e.g. 'Accepted', 'Programmed').
            status (str): The condition status ('True', 'False' or 'Unknown').
            reason (Optional[str]): The machine-readable reason, if reported.
            message (Optional[str]): The human-readable message, if reported.
        """
        self.condition_type = condition_type
        self.status = status
        self.reason = reason
        self.message = message

    @staticmethod
    def build_condition_objects_from_dicts(condition_dicts: list[dict]) -> list["GatewayConditionObject"]:
        """Build condition objects from a parsed 'conditions' list.

        Args:
            condition_dicts (list[dict]): The parsed conditions list of a resource status.

        Returns:
            list[GatewayConditionObject]: One object per condition that has a type and a status.
        """
        return [GatewayConditionObject(condition["type"], condition["status"], condition.get("reason"), condition.get("message")) for condition in condition_dicts if condition.get("type") and condition.get("status")]

    def get_condition_type(self) -> str:
        """Get the condition type.

        Returns:
            str: The condition type.
        """
        return self.condition_type

    def get_status(self) -> str:
        """Get the condition status.

        Returns:
            str: 'True', 'False' or 'Unknown'.
        """
        return self.status

    def get_reason(self) -> Optional[str]:
        """Get the condition reason.

        Returns:
            Optional[str]: The reason, or None when it was not reported.
        """
        return self.reason

    def get_message(self) -> Optional[str]:
        """Get the condition message.

        Returns:
            Optional[str]: The message, or None when it was not reported.
        """
        return self.message

    def is_true(self) -> bool:
        """Check whether the condition status is 'True'.

        Returns:
            bool: True if the status is 'True', False otherwise.
        """
        return self.status == "True"

    def __str__(self) -> str:
        """Human-readable representation of the condition.

        Returns:
            str: The condition type, status and reason.
        """
        return f"{self.condition_type}={self.status} (reason={self.reason})"

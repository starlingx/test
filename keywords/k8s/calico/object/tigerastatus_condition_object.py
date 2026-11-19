"""Object for one condition of the Calico TigeraStatus resource."""

from typing import Optional


class TigeraStatusConditionObject:
    """One entry of status.conditions in 'kubectl get tigerastatus calico -o yaml'."""

    def __init__(self, condition_type: str, status: str, reason: Optional[str], message: Optional[str]):
        """Initialize the condition.

        Args:
            condition_type (str): The condition type (e.g. 'Available', 'Degraded', 'Progressing').
            status (str): The condition status ('True', 'False' or 'Unknown').
            reason (Optional[str]): The machine-readable reason, if reported.
            message (Optional[str]): The human-readable message, if reported.
        """
        self.condition_type = condition_type
        self.status = status
        self.reason = reason
        self.message = message

    def get_condition_type(self) -> str:
        """Get the condition type.

        Returns:
            str: The condition type (e.g. 'Available').
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
            Optional[str]: The reason, or None when the operator did not report one.
        """
        return self.reason

    def get_message(self) -> Optional[str]:
        """Get the condition message.

        Returns:
            Optional[str]: The message, or None when the operator did not report one.
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
            str: The condition type, status, reason and message.
        """
        return f"{self.condition_type}={self.status} (reason={self.reason}, message={self.message})"

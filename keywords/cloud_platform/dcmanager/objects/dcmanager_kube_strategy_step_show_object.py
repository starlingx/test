from typing import Optional


class DcmanagerKubeStrategyStepObject:
    """
    This class represents a dcmanager kube-strategy-step as an object.
    """

    def __init__(self) -> None:
        """Initializes a DcmanagerKubeStrategyStepObject with default values."""
        self.state: Optional[str] = None

    def set_state(self, state: str):
        """Sets the state of the kube-strategy-step."""
        self.state = state

    def get_state(self) -> Optional[str]:
        """Gets the state of the strategy-step."""
        return self.state

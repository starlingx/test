class SoftwareStateOutput:
    """
    Class to hold attributes of a software state
    """

    def __init__(self, patch_states: dict) -> None:
        """
        Constructor

        Args:
            patch_states (dict): Dictionary containing patch states.
        """
        self.patch_states = patch_states

    def get_state(self, patch_id: str) -> str:
        """
        Get the state for a given patch_id.

        Args:
            patch_id (str): The patch ID to look up.

        Returns:
            str: The state of the patch, or None if not found.
        """
        return self.patch_states.get(patch_id)

class SwPatchQueryObject:
    """Represents an applied software patch returned by the sw-patch query."""

    def __init__(self, patch_id: str, reboot_required: str, release: str, state: str):
        """Initializes a SwPatchQueryObject instance.

        Args:
            patch_id (str): Unique identifier of the patch.
            reboot_required (str): Indicates if a reboot is required.
            release (str): Software release version associated with the patch.
            state (str): Current state of the patch.
        """
        self.patch_id = patch_id
        self.reboot_required = reboot_required
        self.release = release
        self.state = state

    def set_patch_id(self, patch_id):
        """
        Setter for patch_id
        """
        self.patch_id = patch_id

    def get_patch_id(self) -> str:
        """
        Getter for patch_id
        """
        return self.patch_id

    def set_reboot_required(self, reboot_required):
        """
        Setter for reboot_required
        """
        self.reboot_required = reboot_required

    def get_reboot_required(self) -> str:
        """
        Getter for reboot_required
        """
        return self.reboot_required

    def set_release(self, release):
        """
        Setter for release
        """
        self.release = release

    def get_release(self) -> str:
        """
        Getter for release
        """
        return self.release

    def set_state(self, state):
        """
        Setter for state
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for state
        """
        return self.state

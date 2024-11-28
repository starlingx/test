class Capability:
    """
    Class for capability
    """

    def __init__(self, capability_id, capability_name, capability_marker):
        self.capability_id = capability_id
        self.capability_name = capability_name
        self.capability_marker = capability_marker

    def get_capability_id(self) -> int:
        """
        Getter for capability id
        Returns:

        """
        return self.capability_id

    def get_capability_name(self) -> str:
        """
        Getter for capability name
        Returns:

        """
        return self.capability_name

    def get_capability_marker(self) -> str:
        """
        Getter for capability marker
        Returns:

        """
        return self.capability_marker

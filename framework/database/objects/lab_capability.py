class LabCapability:
    """
    Class for Lab capability
    """

    def __init__(self, capability_lab_id: int, lab_info_id: int, capability_id: int):
        self.capability_lab_id = capability_lab_id
        self.lab_info_id = lab_info_id
        self.capability_id = capability_id

    def get_capability_lab_id(self) -> int:
        """
        Getter for capability lab id
        Returns:

        """
        return self.capability_lab_id

    def get_lab_info_id(self) -> int:
        """
        Getter for lab info id
        Returns:

        """
        return self.lab_info_id

    def get_capability_id(self) -> int:
        """
        Getter for capability id
        Returns:

        """
        return self.capability_id

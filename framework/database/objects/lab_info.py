class LabInfo:
    """
    Class for lab info object
    """

    def __init__(self, lab_info_id: int, lab_name: str):
        self.lab_info_id = lab_info_id
        self.lab_name = lab_name

    def get_lab_info_id(self) -> int:
        """
        Getter for lab info id
        Returns:

        """
        return self.lab_info_id

    def get_lab_name(self) -> str:
        """
        Getter for lab name
        Returns: the lab name

        """
        return self.lab_name

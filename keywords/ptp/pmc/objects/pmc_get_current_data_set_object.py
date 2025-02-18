class PMCGetCurrentDataSetObject:
    """
    Object to hold the values of Current data set
    """

    def __init__(self):
        self.steps_removed: int = -1
        self.offset_from_master: float = 0.0
        self.mean_path_delay: float = 0.0

    def get_steps_removed(self) -> int:
        """
        Getter for steps_removed
        Returns: the steps_removed value

        """
        return self.steps_removed

    def set_steps_removed(self, steps_removed: int):
        """
        Setter for steps_removed
        Args:
            steps_removed (): the steps_removed value

        Returns:

        """
        self.steps_removed = steps_removed

    def get_offset_from_master(self) -> float:
        """
        Getter for offset_from_master
        Returns: offset_from_master

        """
        return self.offset_from_master

    def set_offset_from_master(self, offset_from_master: float):
        """
        Setter for offset_from_master
        Args:
            offset_from_master (): the offset_from_master value

        Returns:

        """
        self.offset_from_master = offset_from_master

    def get_mean_path_delay(self) -> float:
        """
        Getter for mean_path_delay
        Returns: mean_path_delay value

        """
        return self.mean_path_delay

    def set_mean_path_delay(self, mean_path_delay: float):
        """
        Setter for mean_path_delay
        Args:
            mean_path_delay (): mean_path_delay value

        Returns:

        """
        self.mean_path_delay = mean_path_delay

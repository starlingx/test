class SoftwareShowObject:
    """
    Class to hold attributes of a software show as returned by
    software show command

    """

    def __init__(
        self,
        property: str,
        value: str,
    ):
        self.property = property
        self.value = value

    def get_property(self) -> str:
        """
        Getter for property

        Returns: the property

        """
        return self.property

    def get_value(self) -> str:
        """
        Getter for value

        Returns: the value

        """
        return self.value

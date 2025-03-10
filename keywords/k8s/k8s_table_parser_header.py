class K8sTableParserHeader:
    """
    Class that holds the position of the header in a k8s table.
    """

    def __init__(self, name, start_position):
        """
        Constructor.
        If we get the output below from a k8s command,

                      11111111112222222222333333333344444444445
            012345678901234567890123456789012345678901234567890
            NAME                                           READY   STATUS
            some-pod-name-c5cfd47-8bpk5                    1/1     Running

        the K8sTableParserHeader for the 'NAME' header would be:

            name: NAME
            start_position: 0
            end_position: 46

        Args:
            name: Name associated with the header.
            start_position: Index at which the header starts

        """
        self.name = name
        self.start_position = start_position
        self.end_position = -1

    def get_name(self) -> str:
        """
        Getter for the name of this Header.
        Returns: name of this header.

        """
        return self.name

    def get_start_position(self) -> int:
        """
        Getter for the starting position of the Header.
        Returns: Index-position of the first character

        """
        return self.start_position

    def set_end_position(self, end_position: int):
        """
        Setter for the of the Header.
        Args:
            end_position:  Index-position of the last space before the next header.

        Returns: None

        """
        self.end_position = end_position

    def get_end_position(self) -> int:
        """
        Getter for the ending position of the Header.
        Returns: Index-position of the last space before the next header.

        """
        return self.end_position

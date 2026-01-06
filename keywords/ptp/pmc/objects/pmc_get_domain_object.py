class PMCGetDomainObject:
    """
    Object to hold the values of DOMAIN
    """

    def __init__(self):
        self.domain_number: int = -1

    def get_domain_number(self) -> int:
        """
        Getter for domain_number

        Returns:
            int: the domain_number value
        """
        return self.domain_number

    def set_domain_number(self, domain_number: int) -> None:
        """
        Setter for domain_number

        Args:
            domain_number (int): the domain_number value

        Returns:
            None: This method does not return anything.
        """
        self.domain_number = domain_number

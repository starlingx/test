class PMCGetDomainObject:
    """
    Object to hold the values of DOMAIN
    """

    def __init__(self):
        self.domain_number: int = -1       

    def get_domain_number(self) -> int:
        """
        Getter for domain_number
        Returns: the domain_number value

        """
        return self.domain_number

    def set_domain_number(self, domain_number: int):
        """
        Setter for domain_number
        Args:
            domain_number : the domain_number value

        Returns:

        """
        self.domain_number = domain_number




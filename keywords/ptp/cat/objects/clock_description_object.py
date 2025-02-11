class ClockDescriptionObject:
    """
    Object to hold the values of Clock description Object
    """

    def __init__(self):
        self.product_description: str = ''
        self.revision_data: str = ''
        self.manufacturer_identity: str = ''
        self.user_description: str = ''
        self.time_source: str = ''

    def get_product_description(self) -> str:
        """
        Getter for product_description
        Returns: product_description

        """
        return self.product_description

    def set_product_description(self, product_description: str):
        """
        Setter for product_description
        Args:
            product_description (): the product_description value

        Returns:

        """
        self.product_description = product_description

    def get_revision_data(self) -> str:
        """
        Getter for revision_data
        Returns: revision_data value

        """
        return self.revision_data

    def set_revision_data(self, revision_data: str):
        """
        Setter for revision_data
        Args:
            revision_data (): revision_data value

        Returns:

        """
        self.revision_data = revision_data

    def get_manufacturer_identity(self) -> str:
        """
        Getter for manufacturer_identity
        Returns: manufacturer_identity value

        """
        return self.manufacturer_identity

    def set_manufacturer_identity(self, manufacturer_identity: str):
        """
        Setter for manufacturer_identity
        Args:
            manufacturer_identity (): manufacturer_identity value

        Returns:

        """
        self.manufacturer_identity = manufacturer_identity

    def get_user_description(self) -> str:
        """
        Getter for user_description
        Returns: the user_description value

        """
        return self.user_description

    def set_user_description(self, user_description: str):
        """
        Setter for user_description
        Args:
            user_description (): the user_description value

        Returns:

        """
        self.user_description = user_description

    def get_time_source(self) -> str:
        """
        Getter for time_source
        Returns: time_source value

        """
        return self.time_source

    def set_time_source(self, time_source: str):
        """
        Setter for time_source
        Args:
            time_source (): the time_source value

        Returns:

        """
        self.time_source = time_source


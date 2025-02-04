class ProductVersion:
    """
    This class models a ProductVersion as an object.
    ProductVersions have names and can also be compared chronologically.
    """

    def __init__(self, version_name: str, version_id: int):
        """
        Constructor
        Args:
            version_name (str): The String name of the Product Version
            version_id (int) : Integers assigned for comparing release order
        """
        self.version_name = version_name
        self.version_id = version_id

    def __str__(self) -> str:
        return self.version_name

    def __hash__(self):
        return hash(self.version_name)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def get_name(self) -> str:
        """
        Getter for the name of this version

        Returns:

        """
        return self.version_name

    def get_id(self) -> int:
        """
        Getter for the id of this version

        Returns:

        """
        return self.version_id

    def is_before_or_equal_to(self, other_product_version) -> bool:
        """
        Returns true if SELF <= other_product_version based on their id.
        Args:
            other_product_version (ProductVersion): The version of comparison

        Returns (bool): SELF <= other_product_version based on their id.
        """
        return self.version_id <= other_product_version.version_id

    def is_after_or_equal_to(self, other_product_version) -> bool:
        """
        Returns true if SELF >= other_product_version based on their id.
        Args:
            other_product_version (ProductVersion): The version of comparison

        Returns (bool): SELF >= other_product_version based on their id.
        """
        return self.version_id >= other_product_version.version_id


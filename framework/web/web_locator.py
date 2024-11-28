class WebLocator:

    def __init__(self, locator: str, by: str):
        """
        Constructor
        Args:
            locator: The locator that we want to use to target this element.
            by: The type of locator that is used.
        """

        self.locator = locator
        self.by = by

    def get_locator(self):
        """
        Getter for the locator.
        Returns:

        """
        return self.locator

    def get_by(self):
        """
        Getter for the Type of Locator
        Returns:

        """
        return self.by

    def __str__(self):
        """
        String representation of this object.
        Returns:

        """
        return f"{self.by}: {self.locator}"

class SystemServiceParameterObject:
    """
    Class to represent a single service parameter.
    """

    # Constructor
    def __init__(self, service="", section="", name="", value="", uuid="", modified_value=""):
        self.service = service
        self.section = section
        self.name = name
        self.value = value

        # Additional fields
        self.uuid = uuid  # Will be available if saved in the database
        self.modified_value = modified_value  # 2nd value for the 'modify' case

    def __eq__(self, other):
        """Check equality based on service, section, name, and value."""
        if not isinstance(other, SystemServiceParameterObject):
            return False

        # For comparisons ignore 'uuid' and 'value2'
        return self.get_service() == other.get_service() and self.get_section() == other.get_section() and self.get_name() == other.get_name() and self.get_value() == other.get_value()

    def __repr__(self):
        """Return string representation for debugging."""
        return f"{vars(self)}"

    def __str__(self):
        """Return string representation."""
        return f"{vars(self)}"

    def set_service(self, service: str):
        """Setter for service"""
        self.service = service

    def get_service(self) -> str:
        """Getter for service"""
        return self.service

    def set_section(self, section: str):
        """Setter for section"""
        self.section = section

    def get_section(self) -> str:
        """Getter for section"""
        return self.section

    def set_name(self, name: str):
        """Setter for name"""
        self.name = name

    def get_name(self) -> str:
        """Getter for name"""
        return self.name

    def set_value(self, value: str):
        """Setter for value"""
        self.value = value

    def get_value(self) -> str:
        """Getter for value"""
        return self.value

    def set_uuid(self, uuid: str):
        """Setter for uuid"""
        self.uuid = uuid

    def get_uuid(self) -> str:
        """Getter for uuid"""
        return self.uuid

    def set_modified_value(self, modified_value: str):
        """Setter for modified_value"""
        self.modified_value = modified_value

    def get_modified_value(self) -> str:
        """Getter for modified_value"""
        return self.modified_value

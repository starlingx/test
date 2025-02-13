class SystemLoadObject:
    """
    This class represents a service as an object.
    This is typically a line in the system load output table.
    """

    def __init__(self):
        self.id:int = -1
        self.state:str = None
        self.software_version:str = None
        self.compatible_version:str = None
        self.required_patches: str = None


    def set_id(self, load_id: int):
        """
        Setter for the id
        """
        self.id = load_id

    def get_id(self) -> int:
        """
        Getter for the id
        """
        return self.id

    def set_state(self, state: str):
        """
        Setter for the state
        """
        self.state = state

    def get_state(self) -> str:
        """
        Getter for state
        """
        return self.state

    def set_software_version(self, software_version: str):
        """
        Setter for the software_version
        """
        self.software_version = software_version

    def get_software_version(self) -> str:
        """
        Getter for the software_version
        """
        return self.software_version

    def set_compatible_version(self, compatible_version: str):
        """
        Setter for the compatible_version
        """
        self.compatible_version = compatible_version

    def get_compatible_version(self) -> str:
        """
        Getter for the compatible_version
        """
        return self.compatible_version

    def set_required_patches(self, required_patches: str):
        """
        Setter for required_patches
        """
        self.required_patches = required_patches

    def get_required_patches(self) -> str:
        """
        Getter for required_patches
        """
        return self.required_patches
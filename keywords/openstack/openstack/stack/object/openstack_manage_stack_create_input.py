class OpenstackManageStackCreateInput:
    """
    Class to support the parameters for managing OpenStack stacks.
    """

    def __init__(self):
        self.resource_list = None
        self.file_destination = None

    def set_resource_list(self, resource_list: dict):
        """
        Setter for the 'resource_list' property.
        """
        self.resource_list = resource_list

    def get_resource_list(self) -> dict:
        """
        Getter for the 'resource_list' property.
        """
        return self.resource_list

    def set_file_destination(self, file_destination: str):
        """
        Setter for the 'file_destination' property.
        """
        self.file_destination = file_destination

    def get_file_destination(self) -> str:
        """
        Getter for the 'file_destination' property.
        """
        return self.file_destination

class OpenstackManageStackDeleteInput:
    """
    Class to support the parameters for managing OpenStack stacks.
    """

    def __init__(self):
        self.resource_list = None
        self.skip_list = []

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

    def set_skip_list(self, skip_list: list):
        """
        Setter for the 'skip_list' property.
        """
        self.skip_list = skip_list

    def get_skip_list(self) -> list:
        """
        Getter for the 'skip_list' property.
        """
        return self.skip_list

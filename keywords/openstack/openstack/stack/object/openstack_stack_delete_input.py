class OpenstackStackDeleteInput:
    """
    Class to support the parameters for 'openstack stack delete' command.
    An example of using this command is:

        'openstack stack delete hello-kitty'

    Where:
         hello-kitty: the name of the application that you want to delete.

    """

    def __init__(self):
        """
        Constructor
        """
        self.app_name = None
        self.force_deletion = False

    def get_stack_name(self) -> str:
        """
        Getter for this 'stack_name' parameter.
        """
        return self.stack_name

    def set_stack_name(self, stack_name: str):
        """
        Setter for the 'stack_name' parameter.
        """
        self.stack_name = stack_name

class SystemApplicationDeleteInput:
    """
    Class to support the parameters for 'system application-delete' command.
    An example of using this command is:

        'system application-delete -f hello-kitty'

    Where:
        -f: Forces the deletion of the application, ignoring certain security or dependency checks. This can be useful if
         you want to delete the application quickly, even if it still has active components or dependencies.

         hello-kitty: the name of the application that you want to delete.

    """

    def __init__(self):
        """
        Constructor
        """
        self.app_name = None
        self.force_deletion = False

    def get_app_name(self) -> str:
        """
        Getter for this 'app_name' parameter.
        """
        return self.app_name

    def set_app_name(self, app_name: str):
        """
        Setter for the 'app_name' parameter.
        """
        self.app_name = app_name

    def get_force_deletion(self) -> bool:
        """
        Getter for this 'force_deletion' parameter.
        """
        return self.force_deletion

    def set_force_deletion(self, force_deletion: bool):
        """
        Setter for the 'force_deletion' parameter.
        """
        self.force_deletion = force_deletion

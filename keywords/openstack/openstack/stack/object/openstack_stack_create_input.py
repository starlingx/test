class OpenstackStackCreateInput:
    """
    Class to support the parameters for 'openstack stack create' command.
    An example of using this command is:

        'openstack stack create --template=file/location/stack.yaml'

    This class is able to generate this command just by previously setting the parameters.
    """

    def __init__(self):
        """
        Constructor
        """
        self.stack_name = None
        self.template_file_name = None
        self.template_file_path = 'heat'
        self.return_format = 'json'

    def set_stack_name(self, stack_name: str):
        """
        Setter for the 'stack_name' parameter.
        """
        self.stack_name = stack_name

    def get_stack_name(self) -> str:
        """
        Getter for this 'stack_name' parameter.
        """
        return self.stack_name

    def set_template_file_name(self, template_file_name: str):
        """
        Setter for the 'template_file_name' parameter.
        """
        self.template_file_name = template_file_name

    def get_template_file_name(self) -> str:
        """
        Getter for this 'template_file_name' parameter.
        """
        return self.template_file_name

    def set_template_file_path(self, template_file_path: str):
        """
        Setter for the 'template_file_path' parameter.
        """
        self.template_file_path = template_file_path

    def get_template_file_path(self) -> str:
        """
        Getter for this 'template_file_path' parameter.
        """
        return self.template_file_path

    def set_return_format(self, return_format: str) -> str:
        """
        Getter for this 'get_return_format' parameter.
        """
        self.return_format = return_format

    def get_return_format(self) -> str:
        """
        Getter for this 'return_format' parameter.
        """
        return self.return_format
class OpenstackStackObject:
    """
    Class to handle data provided by commands such as 'openstack stack create'

    Example:
        'openstack stack create --template=heat/project_stack.yaml stack_test -f json'
        {
            "id": "1bb26a3c",
            "stack_name": "stack_test",
            "description": "Heat template to create OpenStack projects.\n",
            "creation_time": "2025-04-10T13:35:04Z",
            "updated_time": null,
            "stack_status": "CREATE_COMPLETE",
            "stack_status_reason": "Stack CREATE completed successfully"
        }
    """

    def __init__(self):
        """
        Constructor.
        """
        self.id: str
        self.stack_name: str
        self.description: str
        self.creation_time: str
        self.updated_time: str
        self.stack_status: str
        self.stack_status_reason: str

    def set_id(self, id: str):
        """
        Setter for the 'id' property.
        """
        self.id = id

    def get_id(self) -> str:
        """
        Getter for this 'id' property.
        """
        return self.id

    def set_stack_name(self, stack_name: str):
        """
        Setter for the 'stack_name' property.
        """
        self.stack_name = stack_name

    def get_stack_name(self) -> str:
        """
        Getter for the 'stack_name' property.
        """
        return self.stack_name

    def set_description(self, description: str):
        """
        Setter for the 'description' property.
        """
        self.description = description

    def get_description(self) -> str:
        """
        Getter for the 'description' property.
        """
        return self.description

    def set_creation_time(self, creation_time: str):
        """
        Setter for the 'creation_time' property.
        """
        self.creation_time = creation_time

    def get_creation_time(self) -> str:
        """
        Getter for the 'creation_time' property.
        """
        return self.creation_time

    def set_updated_time(self, updated_time: str):
        """
        Setter for the 'updated_time' property.
        """
        self.updated_time = updated_time

    def get_updated_time(self) -> str:
        """
        Getter for the 'updated_time' property.
        """
        return self.updated_time

    def set_stack_status(self, stack_status: str):
        """
        Setter for the 'stack_status' property.
        """
        self.stack_status = stack_status

    def get_stack_status(self) -> str:
        """
        Getter for the 'stack_status' property.
        """
        return self.stack_status

    def set_stack_status_reason(self, stack_status_reason: str):
        """
        Setter for the 'stack_status_reason' property.
        """
        self.stack_status_reason = stack_status_reason

    def get_stack_status_reason(self) -> str:
        """
        Getter for the 'stack_status_reason' property.
        """
        return self.stack_status_reason
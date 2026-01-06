class OpenstackStackListObject:
    """
    Class to handle the data provided by the 'openstack stack list' command execution. This command generates the
    output table shown below, where each object of this class represents a single row in that table.

    +----------+------------+----------+-----------------+----------------------+--------------+
    | ID       | Stack Name | Project  | Stack Status    | Creation Time        | Updated Time |
    +----------+------------+----------+-----------------+----------------------+--------------+
    | 1bb26a3c | stack_test | a3c1bb26 | CREATE_COMPLETE | 2025-04-10T12:31:03Z | None         |
    +----------+------------+----------+-----------------+----------------------+--------------+

    """

    def __init__(
        self,
        id: str,
        stack_name: str,
        project: str,
        stack_status: str,
        creation_time: str,
        updated_time: str,
    ):
        self.id = id
        self.stack_name = stack_name
        self.project = project
        self.stack_status = stack_status
        self.creation_time = creation_time
        self.updated_time = updated_time

    def get_id(self) -> str:
        """
        Getter for id
        Returns: the id

        """
        return self.id

    def get_stack_name(self) -> str:
        """
        Getter for stack name
        Returns: the stack name

        """
        return self.stack_name

    def get_project(self) -> str:
        """
        Getter for project
        Returns: the project

        """
        return self.project

    def get_stack_status(self) -> str:
        """
        Getter for stack status
        Returns: the stack status

        """
        return self.stack_status

    def get_creation_time(self) -> str:
        """
        Getter for creation time
        Returns: the creation time

        """
        return self.creation_time

    def get_updated_time(self) -> str:
        """
        Getter for updated time
        Returns: the updated time

        """
        return self.updated_time

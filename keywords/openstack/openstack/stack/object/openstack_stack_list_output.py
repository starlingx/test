from framework.exceptions.keyword_exception import KeywordException
from framework.logging.automation_logger import get_logger
from keywords.openstack.openstack.stack.object.openstack_stack_list_object import OpenstackStackListObject
from keywords.openstack.openstack.openstack_json_parser import OpenstackJsonParser


class OpenstackStackListOutput:
    """
    This class parses the output of the command 'openstack stack list'
    The parsing result is a 'OpenstackStackListObject' instance.

    Example:
        'openstack stack list'
        +----------+------------+----------+-----------------+----------------------+--------------+
        | ID       | Stack Name | Project  | Stack Status    | Creation Time        | Updated Time |
        +----------+------------+----------+-----------------+----------------------+--------------+
        | 1bb26a3c | stack_test | a3c1bb26 | CREATE_COMPLETE | 2025-04-10T12:31:03Z | None         |
        +----------+------------+----------+-----------------+----------------------+--------------+

    """

    def __init__(self, openstack_stack_list_output):
        """
        Constructor
        Args:
            openstack_stack_list_output: the output of the command 'openstack stack list'.
        """
        self.openstack_stacks: [OpenstackStackListObject] = []
        openstack_json_parser = OpenstackJsonParser(openstack_stack_list_output)
        output_values = openstack_json_parser.get_output_values_list()

        for value in output_values:
            if self.is_valid_output(value):
                self.openstack_stacks.append(
                    OpenstackStackListObject(
                        value['ID'],
                        value['Stack Name'],
                        value['Project'],
                        value['Stack Status'],
                        value['Creation Time'],
                        value['Updated Time'],
                    )
                )
            else:
                raise KeywordException(f"The output line {value} was not valid")

    def get_stacks(self) -> [OpenstackStackListObject]:
        """
        Returns the list of stack objects
        Returns:

        """
        return self.openstack_stacks

    def get_stack(self, stack_name: str) -> OpenstackStackListObject:
        """
        Gets the given stack
        Args:
            stack_name (): the name of the stack

        Returns: the stack object

        """
        stacks = list(filter(lambda stack: stack.get_stack_name() == stack_name, self.openstack_stacks))
        if len(stacks) == 0:
            raise KeywordException(f"No stack with name {stack_name} was found.")

        return stacks[0]

    @staticmethod
    def is_valid_output(value):
        """
        Checks to ensure the output has the correct keys
        Args:
            value (): the value to check

        Returns:

        """
        valid = True
        if 'ID' not in value:
            get_logger().log_error(f'id is not in the output value: {value}')
            valid = False
        if 'Stack Name' not in value:
            get_logger().log_error(f'stack name is not in the output value: {value}')
            valid = False
        if 'Project' not in value:
            get_logger().log_error(f'project is not in the output value: {value}')
            valid = False
        if 'Stack Status' not in value:
            get_logger().log_error(f'stack status is not in the output value: {value}')
            valid = False
        if 'Creation Time' not in value:
            get_logger().log_error(f'creation time is not in the output value: {value}')
            valid = False

        return valid

    def is_in_stack_list(self, stack_name: str) -> bool:
        """
        Verifies if there is an stack with the name 'stack_name'.

        Args:
             stack_name (str): a string representing the stack's name.

        Returns:
             bool: True if there is a stack with the name 'stack_name'; False otherwise.
        """
        stacks = list(filter(lambda stack: stack.get_stack() == stack_name, self.openstack_stacks))
        if len(stacks) == 0:
            return False
        return True

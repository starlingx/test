from keywords.openstack.openstack.stack.object.openstack_stack_object import OpenstackStackObject
from keywords.openstack.openstack.openstack_json_parser import OpenstackJsonParser

class OpenstackStackOutput:
    """
    This class parses the output of commands such as 'openstack stack create'
    that share the same output as shown in the example below.
    The parsing result is a 'openstackStackObject' instance.

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

    def __init__(self, openstack_stack_output):
        """
        Constructor.
            Create an internal OpenstackStackCreateObject from the passed parameter.
        Args:
            openstack_stack_output (list[str]): a list of strings representing the output of the
            'openstack stack create' command.

        """
        openstack_json_parser = OpenstackJsonParser(openstack_stack_output)

        output_values = openstack_json_parser.get_output_values_list()
        self.openstack_stack_object = OpenstackStackObject()

        if 'id' in output_values:
            self.openstack_stack_object.set_id(output_values['id'])

        if 'stack_name' in output_values:
            self.openstack_stack_object.set_stack_name(output_values['stack_name'])

        if 'description' in output_values:
            self.openstack_stack_object.set_description(output_values['description'])

        if 'creation_time' in output_values:
            self.openstack_stack_object.set_creation_time(output_values['creation_time'])

        if 'updated_time' in output_values:
            self.openstack_stack_object.set_updated_time(output_values['updated_time'])

        if 'stack_status' in output_values:
            self.openstack_stack_object.set_stack_status(output_values['stack_status'])

        if 'stack_status_reason' in output_values:
            self.openstack_stack_object.set_stack_status_reason(output_values['stack_status_reason'])

    def get_openstack_stack_object(self) -> OpenstackStackObject:
        """
        Getter for OpenstackStackObject object.

        Returns:
            A OpenstackStackObject instance representing the output of commands sucha as 'openstack stack create'.

        """
        return self.openstack_stack_object

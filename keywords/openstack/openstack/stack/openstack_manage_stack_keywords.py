from framework.resources.resource_finder import get_stx_resource_path
from framework.logging.automation_logger import get_logger
from keywords.openstack.openstack.openstack_replacement_dict_parser import OpenstackReplacementDictParser
from keywords.files.yaml_keywords import YamlKeywords
from keywords.openstack.openstack.stack.object.openstack_manage_stack_create_input import OpenstackManageStackCreateInput
from keywords.openstack.openstack.stack.object.openstack_manage_stack_delete_input import \
    OpenstackManageStackDeleteInput
from keywords.openstack.openstack.stack.object.openstack_stack_delete_input import OpenstackStackDeleteInput
from keywords.openstack.openstack.stack.openstack_stack_create_keywords import OpenstackStackCreateKeywords
from keywords.openstack.openstack.stack.object.openstack_stack_create_input import OpenstackStackCreateInput
from keywords.openstack.openstack.stack.openstack_stack_delete_keywords import OpenstackStackDeleteKeywords
from keywords.openstack.openstack.stack.openstack_stack_list_keywords import OpenstackStackListKeywords


class OpenstackManageStack:
    """
    Class for Managing stacks support
    """

    def __init__(self, ssh_connection):
        self.ssh_connection = ssh_connection

    def create_stacks(self, openstack_manage_stack_create_input: OpenstackManageStackCreateInput):
        """
        Executes a sequence of stack_create commands based on a OpenstackManageStackCreateInput given
        Validates if given stack is already created before creating it again

        Args: OpenstackManageStackCreateInput

        Returns: None
        """

        resource_list = openstack_manage_stack_create_input.get_resource_list()
        file_destination_location = openstack_manage_stack_create_input.get_file_destination()

        if resource_list is None or file_destination_location is None:
            error_message = "resource_list and file_destination_location are required"
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        for key, values in resource_list.items():
            for value in values:
                stack_name = f"{key}_{value['name']}"
                if OpenstackStackCreateKeywords.is_already_created(stack_name):
                    continue
                output_file_name = f"{stack_name}.yaml"
                template_file = get_stx_resource_path(f"resources/openstack/stack/template/{key}.yaml")
                replacement_dictionary = OpenstackReplacementDictParser(value, key).get_replacement_dict()
                YamlKeywords(self.ssh_connection).generate_yaml_file_from_template(
                    template_file, replacement_dictionary,
                    output_file_name,
                    file_destination_location
                )
                openstack_stack_create = OpenstackStackCreateInput()
                openstack_stack_create.set_stack_name(stack_name)
                openstack_stack_create.set_template_file_name(output_file_name)

                OpenstackStackCreateKeywords(self.ssh_connection).openstack_stack_create(openstack_stack_create)

    def delete_stacks(self, openstack_manage_stack_delete_input: OpenstackManageStackDeleteInput):
        """
        Executes a sequence of stack_delete commands based on a OpenstackManageStackDeleteInput given
        Will not delete stacks listed in the skip_list of that ManageStackDeleteInput
        Gets all existing stacks and if a stack with the given file exists, it will delete it

        Args: OpenstackManageStackDeleteInput

        Returns: None
        """

        resource_list = openstack_manage_stack_delete_input.get_resource_list()
        skip_list = openstack_manage_stack_delete_input.get_skip_list()

        if resource_list is None:
            error_message = "resource_list is required"
            get_logger().log_exception(error_message)
            raise ValueError(error_message)

        openstack_stack_list = OpenstackStackListKeywords(self.ssh_connection).get_openstack_stack_list().get_stacks()
        for key, values in resource_list.items():
            if key in skip_list:
               continue
            for value in values:
                stack_name = f"{key}_{value['name']}"
                if stack_name in openstack_stack_list:
                    openstack_stack_delete_input = OpenstackStackDeleteInput()
                    openstack_stack_delete_input.set_stack_name(stack_name)
                    OpenstackStackDeleteKeywords(self.ssh_connection).get_openstack_stack_delete(openstack_stack_delete_input)
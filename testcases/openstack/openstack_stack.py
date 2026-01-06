from pytest import mark
from framework.resources.resource_finder import get_stx_resource_path
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.files.yaml_keywords import YamlKeywords
from keywords.openstack.openstack.stack.object.openstack_manage_stack_delete_input import \
    OpenstackManageStackDeleteInput
from keywords.openstack.openstack.stack.openstack_manage_stack_keywords import OpenstackManageStack
from keywords.openstack.openstack.stack.object.openstack_manage_stack_create_input import OpenstackManageStackCreateInput
from keywords.openstack.openstack.stack.object.openstack_stack_delete_input import OpenstackStackDeleteInput
from keywords.openstack.openstack.stack.openstack_stack_delete_keywords import OpenstackStackDeleteKeywords
from keywords.openstack.openstack.stack.openstack_stack_list_keywords import OpenstackStackListKeywords


@mark.p1
def test_project_stack_create_and_delete():
    """
    Tests the build of a simple Openstack lab environment using a YAML file and the openstack stack create command

    Test Steps:
        - loads a basic YAML file containing environment properties
        - connect to active controller
        - creates a folder to store generated heat templates
        - generates/uploads a heat template file in the remote repository
        - goes by each object of that YAML file and create that resource using the uploaded template
        and openstack stack create command
        - does not generate Neutron related resources
    """
    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    heat_file_destination = "/var/opt/openstack/heat"

    lab_config_file_location = get_stx_resource_path("resources/openstack/stack/regression/basic_openstack_project_config.yaml")
    lab_config = YamlKeywords(ssh_connection).load_yaml(lab_config_file_location)
    FileKeywords(ssh_connection).create_directory(heat_file_destination)

    openstack_manage_stack_creation = OpenstackManageStackCreateInput()
    openstack_manage_stack_creation.set_file_destination(heat_file_destination)
    openstack_manage_stack_creation.set_resource_list(lab_config)
    OpenstackManageStack(ssh_connection).create_stacks(openstack_manage_stack_creation)

    lab_connect_keywords = LabConnectionKeywords()
    ssh_connection = lab_connect_keywords.get_active_controller_ssh()

    lab_config_file_location = get_stx_resource_path("resources/openstack/stack/regression/basic_openstack_project_config.yaml")
    lab_config = YamlKeywords(ssh_connection).load_yaml(lab_config_file_location)

    openstack_manage_stack_deletion = OpenstackManageStackDeleteInput()
    openstack_manage_stack_deletion.set_resource_list(lab_config)

    OpenstackManageStack(ssh_connection).delete_stacks(openstack_manage_stack_deletion)
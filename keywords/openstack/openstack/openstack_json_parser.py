import json

class OpenstackJsonParser:
    """
    Class for Openstack json parsing

    Sample JSON:
    {
        "ID": "1bb26a3c-5a7a-4eb4-8c70-73ef4b93327d",
        "Stack Name": "stack_test",
        "Project": "f42e14df49524f8eb1fd0665b21122cd",
        "Stack Status": "CREATE_COMPLETE",
        "Creation Time": "2025-04-10T12:31:03Z",
        "Updated Time": null
    }
    """

    def __init__(self, system_output):
        openstack_stack_output_string = ''.join(system_output)
        json_part = openstack_stack_output_string.split('\n', 1)[1]
        self.system_output = json_part

    def get_output_values_list(self):
        """
        Getter for output values list
        Returns: the output values list

        """
        return json.loads(self.system_output)

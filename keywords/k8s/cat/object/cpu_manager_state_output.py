import json5
from keywords.k8s.cat.object.cpu_manager_state_object import CpuManagerStateObject


class CpuManagerStateOutput:

    def __init__(self, cpu_manager_state_output: str):
        """
        Constructor

        Args:
            cpu_manager_state_output: Raw string output from running a "cat /var/lib/kubelet/cpu_manager_state" command.

        """

        dictionary_output = json5.loads(cpu_manager_state_output)
        self.cpu_manager_state_object: CpuManagerStateObject = CpuManagerStateObject()

        if "policyName" in dictionary_output:
            self.cpu_manager_state_object.set_policy_name(dictionary_output['policyName'])
        if "entries" in dictionary_output:
            self.cpu_manager_state_object.set_entries(dictionary_output['entries'])

    def get_cpu_manager_state_object(self) -> CpuManagerStateObject:
        """
        Getter for the cpu_manager_state_object parsed out from the output.
        Returns: CpuManagerStateObject

        """
        return self.cpu_manager_state_object

import json

from keywords.k8s.systeminventory.object.kubectl_systeminventory_object import KubectlSystemInventoryObject


class KubectlSystemInventoryOutput:
    """
    Output class for parsing kubectl get systeminventory JSON output.
    """

    def __init__(self, command_output: list[str] | str, sysinv_name: str):
        """
        Constructor.

        Parse kubectl get JSON output and create internal KubectlSystemInventoryObject.

        Args:
            command_output (list[str] | str): Raw command output from kubectl get -o json
            sysinv_name (str): Name of the SystemInventory resource
        """
        self.kubectl_systeminventory_object = KubectlSystemInventoryObject(sysinv_name)

        # Parse JSON output
        if isinstance(command_output, list):
            command_output = "".join(command_output)

        json_obj = json.loads(command_output)

        # Parse metadata
        metadata = json_obj.get("metadata", {})
        namespace = metadata.get("namespace")
        if namespace:
            self.kubectl_systeminventory_object.set_namespace(namespace)

        # Parse labels
        labels = metadata.get("labels", {})
        for key, value in labels.items():
            self.kubectl_systeminventory_object.set_label(key, value)

        # Get sysinv-creation-status from labels
        status = labels.get("sysinv-creation-status")
        if status:
            self.kubectl_systeminventory_object.set_status(status)

    def get_kubectl_systeminventory_object(self) -> KubectlSystemInventoryObject:
        """
        Get the SystemInventory object.

        Returns:
            KubectlSystemInventoryObject: The SystemInventory object
        """
        return self.kubectl_systeminventory_object

    def get_status(self) -> str | None:
        """
        Get the creation status.

        Returns:
            str | None: Status value or None
        """
        return self.kubectl_systeminventory_object.get_status()

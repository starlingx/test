from keywords.k8s.volumesnapshots.object.kubectl_get_volumesnapshots_table_parser import KubectlGetVolumesnapshotsTableParser
from keywords.k8s.volumesnapshots.object.kubectl_volumesnapshot_object import KubectlVolumesnapshotObject


class KubectlGetVolumesnapshotsOutput:
    """
    A class to interact with and retrieve information about Kubernetes volumesnapshots.snapshot.storage.k8s.io.

    This class provides methods to filter and retrieve volumesnapshot information
    using the `kubectl` command output.
    """

    def __init__(self, kubectl_get_volumesnapshots_output: str):
        """
        Constructor

        Args:
            kubectl_get_volumesnapshots_output (str): Raw string output from running a "kubectl get volumesnapshots" command.
        """
        self.kubectl_volumesnapshot: [KubectlVolumesnapshotObject] = []
        kubectl_get_volumesnapshots_table_parser = KubectlGetVolumesnapshotsTableParser(kubectl_get_volumesnapshots_output)
        output_values_list = kubectl_get_volumesnapshots_table_parser.get_output_values_list()

        for volumesnapshot_dict in output_values_list:

            if "NAME" not in volumesnapshot_dict:
                raise ValueError(f"There is no NAME associated with the volumesnapshot: {volumesnapshot_dict}")

            volumesnapshot = KubectlVolumesnapshotObject(volumesnapshot_dict["NAME"])

            if "READYTOUSE" in volumesnapshot_dict:
                volumesnapshot.set_ready_to_use(volumesnapshot_dict["READYTOUSE"])

            if "SOURCEPVC" in volumesnapshot_dict:
                volumesnapshot.set_source_pvc(volumesnapshot_dict["SOURCEPVC"])

            if "SOURCESNAPSHOTCONTENT" in volumesnapshot_dict:
                volumesnapshot.set_source_snapshot_content(volumesnapshot_dict["SOURCESNAPSHOTCONTENT"])

            if "RESTORESIZE" in volumesnapshot_dict:
                volumesnapshot.set_restore_size(volumesnapshot_dict["RESTORESIZE"])

            if "SNAPSHOTCLASS" in volumesnapshot_dict:
                volumesnapshot.set_snapshot_class(volumesnapshot_dict["SNAPSHOTCLASS"])

            if "SNAPSHOTCONTENT" in volumesnapshot_dict:
                volumesnapshot.set_snapshot_content(volumesnapshot_dict["SNAPSHOTCONTENT"])

            if "CREATIONTIME" in volumesnapshot_dict:
                volumesnapshot.set_creation_time(volumesnapshot_dict["CREATIONTIME"])

            if "AGE" in volumesnapshot_dict:
                volumesnapshot.set_age(volumesnapshot_dict["AGE"])

            self.kubectl_volumesnapshot.append(volumesnapshot)

    def get_volumesnapshot(self, volumesnapshot_name: str) -> KubectlVolumesnapshotObject:
        """
        This function will get the volumesnapshot with the name specified from this get_volumesnapshots_output.

        Args:
            volumesnapshot_name (str): The name of the volumesnapshot of interest.

        Returns:
            KubectlVolumesnapshotObject: The volumesnapshot object with the name specified.

        Raises:
            ValueError: If the volumesnapshot with the specified name does not exist in the output.
        """
        for volumesnapshot in self.kubectl_volumesnapshot:
            if volumesnapshot.get_name() == volumesnapshot_name:
                return volumesnapshot
        else:
            raise ValueError(f"There is no volumesnapshot with the name {volumesnapshot_name}.")

    def get_volumesnapshots(self) -> [KubectlVolumesnapshotObject]:
        """
        Gets all volumesnapshots.

        Returns:
            [KubectlVolumesnapshotObject]: A list of all volumesnapshots.

        """
        return self.kubectl_volumesnapshot

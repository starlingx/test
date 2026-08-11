"""Output parser for 'kubectl get systems' command."""

from keywords.k8s.crd.object.kubectl_systems_object import KubectlSystemsObject
from keywords.k8s.crd.object.kubectl_systems_table_parser import KubectlSystemsTableParser


class KubectlSystemsOutput:
    """Parses the output of 'kubectl get systems' command."""

    def __init__(self, kubectl_get_systems_output: str):
        """Constructor.

        Args:
            kubectl_get_systems_output (str): Raw string output from 'kubectl get systems' command.
        """
        self.kubectl_systems_objects: list[KubectlSystemsObject] = []
        table_parser = KubectlSystemsTableParser(kubectl_get_systems_output)
        output_values_list = table_parser.get_output_values_list()

        for system_dict in output_values_list:
            if "NAME" not in system_dict:
                raise ValueError(f"There is no NAME associated with the system: {system_dict}")

            system_obj = KubectlSystemsObject(system_dict["NAME"])

            if "MODE" in system_dict:
                system_obj.set_mode(system_dict["MODE"])
            if "TYPE" in system_dict:
                system_obj.set_type(system_dict["TYPE"])
            if "VERSION" in system_dict:
                system_obj.set_version(system_dict["VERSION"])
            if "INSYNC" in system_dict:
                system_obj.set_insync(system_dict["INSYNC"])
            if "SCOPE" in system_dict:
                system_obj.set_scope(system_dict["SCOPE"])
            if "RECONCILED" in system_dict:
                system_obj.set_reconciled(system_dict["RECONCILED"])

            self.kubectl_systems_objects.append(system_obj)

    def get_systems(self) -> list[KubectlSystemsObject]:
        """Get all systems objects.

        Returns:
            list[KubectlSystemsObject]: List of all systems objects.
        """
        return self.kubectl_systems_objects

    def get_system(self, name: str) -> KubectlSystemsObject:
        """Get a specific system by name.

        Args:
            name (str): System name.

        Returns:
            KubectlSystemsObject: The system object.

        Raises:
            ValueError: If no system with the specified name is found.
        """
        for system in self.kubectl_systems_objects:
            if system.get_name() == name:
                return system
        raise ValueError(f"There is no system with the name {name}.")

    def is_all_reconciled(self) -> bool:
        """Check if all systems are reconciled.

        Returns:
            bool: True if all systems have reconciled=true.
        """
        return all(s.get_reconciled() == "true" for s in self.kubectl_systems_objects)

    def is_all_insync(self) -> bool:
        """Check if all systems are insync.

        Returns:
            bool: True if all systems have insync=true.
        """
        return all(s.get_insync() == "true" for s in self.kubectl_systems_objects)

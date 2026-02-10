from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.module.object.kubectl_get_module_table_parser import KubectlGetModuleTableParser
from keywords.k8s.module.object.kubectl_module_object import KubectlModuleObject


class KubectlGetModuleOutput:
    """Class to interact with and retrieve information about Kubernetes modules."""

    def __init__(self, kubectl_get_module_output: str | list[str]):
        """Initialize module output.

        Args:
            kubectl_get_module_output (str | list[str]): Raw output from kubectl get module command.
        """
        self.kubectl_module: list[KubectlModuleObject] = []
        kubectl_get_module_table_parser = KubectlGetModuleTableParser(kubectl_get_module_output)
        output_values_list = kubectl_get_module_table_parser.get_output_values_list()

        for module_dict in output_values_list:
            if "NAME" not in module_dict:
                raise KeywordException(f"There is no NAME associated with the module: {module_dict}")

            module = KubectlModuleObject(module_dict["NAME"])

            if "NAMESPACE" in module_dict:
                module.set_namespace(module_dict["NAMESPACE"])

            if "AGE" in module_dict:
                module.set_age(module_dict["AGE"])

            self.kubectl_module.append(module)

    def get_module(self, module_name: str) -> KubectlModuleObject:
        """Get module with specified name.

        Args:
            module_name (str): Name of the module.

        Returns:
            KubectlModuleObject: Module object with specified name.

        Raises:
            KeywordException: If module with specified name does not exist.
        """
        for module in self.kubectl_module:
            if module.get_name() == module_name:
                return module
        raise KeywordException(f"There is no module with the name {module_name}.")

    def get_modules(self) -> list[KubectlModuleObject]:
        """Get all modules.

        Returns:
            list[KubectlModuleObject]: List of all modules.
        """
        return self.kubectl_module

    def module_exists(self, module_name: str) -> bool:
        """Check if module exists.

        Args:
            module_name (str): Name of the module.

        Returns:
            bool: True if module exists, False otherwise.
        """
        try:
            self.get_module(module_name)
            return True
        except KeywordException:
            return False

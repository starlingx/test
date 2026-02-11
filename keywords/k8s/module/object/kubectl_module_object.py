class KubectlModuleObject:
    """Object representing a Kubernetes module resource."""

    def __init__(self, name: str):
        """Initialize module object.

        Args:
            name (str): Name of the module.
        """
        self._name = name
        self._namespace = None
        self._age = None

    def get_name(self) -> str:
        """Get module name.

        Returns:
            str: Module name.
        """
        return self._name

    def set_name(self, name: str) -> None:
        """Set module name.

        Args:
            name (str): Module name.
        """
        self._name = name

    def get_namespace(self) -> str:
        """Get module namespace.

        Returns:
            str: Module namespace.
        """
        return self._namespace

    def set_namespace(self, namespace: str) -> None:
        """Set module namespace.

        Args:
            namespace (str): Module namespace.
        """
        self._namespace = namespace

    def get_age(self) -> str:
        """Get module age.

        Returns:
            str: Module age.
        """
        return self._age

    def set_age(self, age: str) -> None:
        """Set module age.

        Args:
            age (str): Module age.
        """
        self._age = age

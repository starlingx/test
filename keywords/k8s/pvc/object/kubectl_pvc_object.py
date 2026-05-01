class KubectlPvcObject:
    """
    Class to hold attributes of a 'kubectl get pvc' pvc entry.
    """

    def __init__(self, name: str):
        """
        Constructor.

        Args:
            name (str): Name of the pvc.
        """
        self.name = name
        self.namespace = None
        self.status = None
        self.volume = None
        self.capacity = None
        self.access_modes = None
        self.storageclass = None
        self.volumeattributesclass = None
        self.age = None
        self.volumemode = None

    def get_name(self) -> str:
        """
        Getter for NAME entry.

        Returns:
            str: The name of the pvc.
        """
        return self.name

    def set_namespace(self, namespace: str) -> None:
        """
        Setter for NAMESPACE.

        Args:
            namespace (str): Namespace value.
        """
        self.namespace = namespace

    def get_namespace(self) -> str:
        """
        Getter for NAMESPACE entry.

        Returns:
            str: Namespace value.
        """
        return self.namespace

    def set_status(self, status: str) -> None:
        """
        Setter for STATUS.

        Args:
            status (str): status value.
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for STATUS entry.

        Returns:
            str: Status value.
        """
        return self.status

    def set_volume(self, volume: str) -> None:
        """
        Setter for VOLUME.

        Args:
            volume (str): Volume value.
        """
        self.volume = volume

    def get_volume(self) -> str:
        """
        Getter for VOLUME entry.

        Returns:
            str: Volume value.
        """
        return self.volume

    def set_capacity(self, capacity: str) -> None:
        """
        Setter for CAPACITY.

        Args:
            capacity (str): Capacity value.
        """
        self.capacity = capacity

    def get_capacity(self) -> str:
        """
        Getter for CAPACITY entry.

        Returns:
            str: Capacity value.
        """
        return self.capacity

    def set_access_modes(self, access_modes: str) -> None:
        """
        Setter for ACCESS_MODE.

        Args:
            access_modes (str): access_modes value.
        """
        self.access_modes = access_modes

    def get_access_modes(self) -> str:
        """
        Getter for ACCESS_MODE entry.

        Returns:
            str: Access_modes value.
        """
        return self.access_modes

    def set_storageclass(self, storageclass: str) -> None:
        """
        Setter for STORAGECLASS.

        Args:
            storageclass (str): Storageclass address value.
        """
        self.storageclass = storageclass

    def get_storageclass(self) -> str:
        """
        Getter for STORAGECLASS entry.

        Returns:
            str: storageclass value.
        """
        return self.storageclass

    def set_volumeattributesclass(self, volumeattributesclass: str) -> None:
        """
        Setter for VOLUMEATTRIBUTESCLASS.

        Args:
            volumeattributesclass (str): volumeattributesclass value.
        """
        self.volumeattributesclass = volumeattributesclass

    def get_volumeattributesclass(self) -> str:
        """
        Getter for VOLUMEATTRIBUTESCLASS entry.

        Returns:
            str: volumeattributesclass value.
        """
        return self.volumeattributesclass

    def set_age(self, age: str) -> None:
        """
        Setter for AGE.

        Args:
            age (str): Age value.
        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry.

        Returns:
            str: Age value.
        """
        return self.age

    def set_volumemode(self, volumemode: str) -> None:
        """
        Setter for VOLUMEMODE.

        Args:
            volumemode (str): Volumemode value.
        """
        self.volumemode = volumemode

    def get_volumemode(self) -> str:
        """
        Getter for VOLUMEMODE entry.

        Returns:
            str: Volumemode value.
        """
        return self.volumemode

    def __str__(self) -> str:
        """
        String representation of the pvc object.

        Returns:
            str: pvc name and status.
        """
        return f"pvc(name={self.name}, status={self.status})"

    def __repr__(self) -> str:
        """
        Representation of the pvc object.

        Returns:
            str: pvc name and status.
        """
        return self.__str__()

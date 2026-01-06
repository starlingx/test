class KubectlVolumesnapshotObject:
    """
    Class to hold attributes of a 'kubectl get volumesnapshots.snapshot.storage.k8s.io' snapshot entry.
    """

    def __init__(self, name: str):
        """
        Constructor

        Args:
            name (str): Name of the snapshot.
        """
        self.name = name
        self.ready_to_use = None
        self.source_pvc = None
        self.source_snapshot_content = None
        self.restore_size = None
        self.snapshot_class = None
        self.snapshot_content = None
        self.creation_time = None
        self.age = None

    def get_name(self) -> str:
        """
        Getter for NAME entry

        Returns: The name of the snapshot.
        """
        return self.name

    def set_ready_to_use(self, ready_to_use: str) -> None:
        """
        Setter for READYTOUSE

        Args:
            ready_to_use (str): 'true' or 'false'

        Returns: None

        """
        self.ready_to_use = ready_to_use

    def get_ready_to_use(self) -> str:
        """
        Getter for READYTOUSE entry
        """
        return self.ready_to_use

    def set_source_pvc(self, source_pvc: str) -> None:
        """
        Setter for SOURCEPVC

        Args:
            source_pvc (str): source_pvc

        Returns: None

        """
        self.source_pvc = source_pvc

    def get_source_pvc(self) -> str:
        """
        Getter for SOURCEPVC entry
        """
        return self.source_pvc

    def set_source_snapshot_content(self, source_snapshot_content: str) -> None:
        """
        Setter for SOURCESNAPSHOTCONTENT

        Args:
            source_snapshot_content (str): source_snapshot_content

        Returns: None

        """
        self.source_snapshot_content = source_snapshot_content

    def get_source_snapshot_content(self) -> str:
        """
        Getter for SOURCESNAPSHOTCONTENT entry
        """
        return self.source_snapshot_content

    def set_restore_size(self, restore_size: str) -> None:
        """
        Setter for RESTORESIZE

        Args:
            restore_size (str): restore_size

        Returns: None

        """
        self.restore_size = restore_size

    def get_restore_size(self) -> str:
        """
        Getter for RESTORESIZE entry
        """
        return self.restore_size

    def set_snapshot_class(self, snapshot_class: str) -> None:
        """
        Setter for SNAPSHOTCLASS

        Args:
            snapshot_class (str): snapshot_class

        Returns: None

        """
        self.snapshot_class = snapshot_class

    def get_snapshot_class(self) -> str:
        """
        Getter for SNAPSHOTCLASS entry
        """
        return self.snapshot_class

    def set_snapshot_content(self, snapshot_content: str) -> None:
        """
        Setter for SNAPSHOTCONTENT

        Args:
            snapshot_content (str): snapshot_content

        Returns: None

        """
        self.snapshot_content = snapshot_content

    def get_snapshot_content(self) -> str:
        """
        Getter for SNAPSHOTCONTENT entry
        """
        return self.snapshot_content

    def set_creation_time(self, creation_time: str) -> None:
        """
        Setter for CREATIONTIME

        Args:
            creation_time (str): creation time

        Returns: None

        """
        self.creation_time = creation_time

    def get_creation_time(self) -> str:
        """
        Getter for CREATIONTIME entry
        """
        return self.creation_time

    def get_creation_time_in_minutes(self) -> int:
        """
        Converts the creation_time of the snapshot into minutes.

        Returns:
             int: The creation_time of the snapshot in minutes.
        """
        snapshot_creation_time = self.get_creation_time()
        total_minutes = 0

        if "m" in snapshot_creation_time:
            minutes = int(snapshot_creation_time.split("m")[0])
            total_minutes += minutes
        if "h" in snapshot_creation_time:
            hours = int(snapshot_creation_time.split("h")[0])
            total_minutes += hours * 60
        if "d" in snapshot_creation_time:
            days = int(snapshot_creation_time.split("d")[0])
            total_minutes += days * 1440
        if "s" in snapshot_creation_time:
            pass

        return total_minutes

    def set_age(self, age: str) -> None:
        """
        Setter for AGE

        Args:
            age (str): ago

        Returns: None

        """
        self.age = age

    def get_age(self) -> str:
        """
        Getter for AGE entry
        """
        return self.age

    def get_age_in_minutes(self) -> int:
        """
        Converts the age of the snapshot into minutes.

        Returns:
             int: The age of the snapshot in minutes.
        """
        snapshot_age = self.get_age()
        total_minutes = 0

        if "m" in snapshot_age:
            minutes = int(snapshot_age.split("m")[0])
            total_minutes += minutes
        if "h" in snapshot_age:
            hours = int(snapshot_age.split("h")[0])
            total_minutes += hours * 60
        if "d" in snapshot_age:
            days = int(snapshot_age.split("d")[0])
            total_minutes += days * 1440
        if "s" in snapshot_age:
            pass

        return total_minutes

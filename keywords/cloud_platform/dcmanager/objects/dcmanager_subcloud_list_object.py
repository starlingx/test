class DcManagerSubcloudListObject:
    """
    This class represents a subcloud summary as an object.
    This is typically a line in the 'dcmanager subcloud list' command output table, as shown below.

    +----+-----------+------------+--------------+---------------+---------+---------------+-----------------+
    | id | name      | management | availability | deploy status | sync    | backup status | prestage status |
    +----+-----------+------------+--------------+---------------+---------+---------------+-----------------+
    |  5 | subcloud3 | managed    | online       | complete      | in-sync | None          | None            |
    |  6 | subcloud2 | managed    | online       | complete      | in-sync | None          | None            |
    |  7 | subcloud1 | managed    | online       | complete      | in-sync | None          | None            |
    +----+-----------+------------+--------------+---------------+---------+---------------+-----------------+

    """

    def __init__(self, id: str):
        self.id: str = id
        self.name: str
        self.management: str
        self.availability: str
        self.deploy_status: str
        self.sync: str
        self.backup_status: str
        self.prestage_status: str

    def get_id(self) -> str:
        """
        Getter for this Subcloud Id
        """
        return self.id

    def set_id(self, id: int):
        """
        Setter for the Subcloud Id
        """
        self.id = id

    def get_name(self) -> str:
        """
        Getter for the Subcloud Name
        """
        return self.name

    def set_name(self, name: str):
        """
        Setter for the Subcloud Name
        """
        self.name = name

    def get_management(self) -> str:
        """
        Getter for the Subcloud Management
        """
        return self.management

    def set_management(self, management: str):
        """
        Setter for the Subcloud Management
        """
        self.management = management

    # Getter and Setter for availability
    def get_availability(self) -> str:
        """
        Getter for the Subcloud Availability
        """
        return self.availability

    def set_availability(self, availability: str):
        """
        Setter for the Subcloud Availability
        """
        self.availability = availability

    # Getter and Setter for deploy_status
    def get_deploy_status(self) -> str:
        """
        Getter for the Subcloud Deployment Status
        """
        return self.deploy_status

    def set_deploy_status(self, deploy_status: str):
        """
        Setter for the Subcloud Deployment Status
        """
        self.deploy_status = deploy_status

    # Getter and Setter for sync
    def get_sync(self) -> str:
        """
        Getter for the Subcloud Sync Status
        """
        return self.sync

    def set_sync(self, sync: str):
        """
        Setter for the Subcloud Sync Status
        """
        self.sync = sync

    # Getter and Setter for backup_status
    def get_backup_status(self) -> str:
        """
        Getter for the Subcloud Backup Status
        """
        return self.backup_status

    def set_backup_status(self, backup_status: str):
        """
        Setter for the Subcloud Backup Status
        """
        self.backup_status = backup_status

    # Getter and Setter for prestage_status
    def get_prestage_status(self) -> str:
        """
        Getter for the Subcloud Prestage Status
        """
        return self.prestage_status

    def set_prestage_status(self, prestage_status: str):
        """
        Setter for the Subcloud Prestage Status
        """
        self.prestage_status = prestage_status

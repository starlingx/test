class SystemApplicationObject:
    """
    Class to handle data provided by commands such as 'system application-upload', 'system application-apply', and
    others that share the same output format, as shown in the example below.

    Example:
        'system application-upload -n hello-kitty-min-k8s-version.tgz -v 0.1.0 hello-kitty-min-k8s-version.tgz'
        +---------------+----------------------------------+
        | Property      | Value                            |
        +---------------+----------------------------------+
        | active        | False                            |
        | app_version   | 0.1.0                            |
        | created_at    | 2024-10-14T18:11:52.261952+00:00 |
        | manifest_file | fluxcd-manifests                 |
        | manifest_name | hello-kitty-fluxcd-manifests     |
        | name          | hello-kitty                      |
        | progress      | None                             |
        | status        | uploading                        |
        | updated_at    | None                             |
        +---------------+----------------------------------+
    """

    def __init__(self):
        """
        Constructor.
        """
        self.active: bool
        self.app_version: str
        self.created_at: str
        self.manifest_file: str
        self.manifest_name: str
        self.name: str
        self.progress: str
        self.status: str
        self.updated_at: str

    def set_active(self, active: bool):
        """
        Setter for the 'active' property.
        """
        self.active = active

    def get_active(self) -> bool:
        """
        Getter for this 'active' property.
        """
        return self.active

    def set_app_version(self, app_version: str):
        """
        Setter for the 'app_version' property.
        """
        self.app_version = app_version

    def get_app_version(self) -> str:
        """
        Getter for the 'app_version' property.
        """
        return self.app_version

    def set_created_at(self, created_at: str):
        """
        Setter for the 'created_at' property.
        """
        self.created_at = created_at

    def get_created_at(self) -> str:
        """
        Getter for the 'created_at' property.
        """
        return self.created_at

    def set_manifest_file(self, manifest_file: str):
        """
        Setter for the 'manifest_file' property.
        """
        self.manifest_file = manifest_file

    def get_manifest_file(self) -> str:
        """
        Getter for the 'manifest_file' property.
        """
        return self.manifest_file

    def set_manifest_name(self, manifest_name: str):
        """
        Setter for the 'manifest_name' property.
        """
        self.manifest_name = manifest_name

    def get_manifest_name(self) -> str:
        """
        Getter for the 'manifest_name' property.
        """
        return self.manifest_name

    def set_name(self, name: str):
        """
        Setter for the 'name' property.
        """
        self.name = name

    def get_name(self) -> str:
        """
        Getter for the 'name' property.
        """
        return self.name

    def set_progress(self, progress: str):
        """
        Setter for the 'progress' property.
        """
        self.progress = progress

    def get_progress(self) -> str:
        """
        Getter for the 'progress' property.
        """
        return self.progress

    def set_status(self, status: str):
        """
        Setter for the 'status' property.
        """
        self.status = status

    def get_status(self) -> str:
        """
        Getter for the 'status' property.
        """
        return self.status

    def set_updated_at(self, updated_at: str):
        """
        Setter for the 'updated_at' property.
        """
        self.updated_at = updated_at

    def get_updated_at(self) -> str:
        """
        Getter for the 'updated_at' property.
        """
        return self.updated_at

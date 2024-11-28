class SystemApplicationListObject:
    """
    Class to handle the data provided by the 'system application-list' command execution. This command generates the
    output table shown below, where each object of this class represents a single row in that table.

    +--------------------------+-----------+-------------------------------------------+------------------+----------+-----------+
    | application              | version   | manifest name                             | manifest file    | status   | progress  |
    +--------------------------+-----------+-------------------------------------------+------------------+----------+-----------+
    | aaaa-manager             | 24.09-79  | aaaa-manager-fluxcd-manifests             | fluxcd-manifests | applied  | completed |
    | bbbb-storage             | 24.09-25  | bbbb-storage-fluxcd-manifests             | fluxcd-manifests | uploaded | completed |
    | deployment-manager       | 24.09-21  | deployment-manager-fluxcd-manifests       | fluxcd-manifests | applied  | completed |
    | hello-kitty              | 0.1.0     | hello-kitty-fluxcd-manifests              | fluxcd-manifests | applied  | completed |
    | xxxxx-ingress-controller | 24.09-64  | xxxxx-ingress-controller-fluxcd-manifests | fluxcd-manifests | applied  | completed |
    | cccc-auth-apps           | 24.09-59  | cccc-auth-apps-fluxcd-manifests           | fluxcd-manifests | uploaded | completed |
    | platform-integ-apps      | 24.09-141 | platform-integ-apps-fluxcd-manifests      | fluxcd-manifests | applied  | completed |
    | rook-dddd                | 24.09-48  | rook-dddd-fluxcd-manifests                | fluxcd-manifests | uploaded | completed |
    +--------------------------+-----------+-------------------------------------------+------------------+----------+-----------+

    """

    def __init__(
        self,
        application: str,
        version: str,
        manifest_name: str,
        manifest_file,
        status: str,
        progress,
    ):
        self.application = application
        self.version = version
        self.manifest_name = manifest_name
        self.manifest_file = manifest_file
        self.status = status
        self.progress = progress

    def get_application(self) -> str:
        """
        Getter for application
        Returns: the application

        """
        return self.application

    def get_version(self) -> str:
        """
        Getter for version
        Returns: the version

        """
        return self.version

    def get_manifest_name(self) -> str:
        """
        Getter for manifest name
        Returns: the manifest name

        """
        return self.manifest_name

    def get_manifest_file(self) -> str:
        """
        Getter for manifest file
        Returns: the manifest file

        """
        return self.manifest_file

    def get_status(self) -> str:
        """
        Getter for status
        Returns: the status

        """
        return self.status

    def get_progress(self) -> str:
        """
        Getter for progress
        Returns: the progress

        """
        return self.progress

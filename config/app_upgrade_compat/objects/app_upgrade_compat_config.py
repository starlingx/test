import json5


class AppUpgradeCompatConfig:
    """
    This class holds the configuration for the application platform-upgrade compatibility tests.

    It carries data only: the release being upgraded to, and the name and namespace of the
    application to act on. What a test does with that data - which steps it runs, what it asserts,
    which phases it checks - lives in the test case, not here.
    """

    def __init__(self, config_path: str):
        """
        Load and parse the application upgrade compatibility config file.

        Args:
            config_path(str): path to the JSON5 config file.

        Raises:
            FileNotFoundError: when the config file cannot be found.

        """
        with open(config_path) as config_file:
            config_dict = json5.load(config_file)
        self.to_version = config_dict.get("to_version")
        self.applications = config_dict.get("applications", {})

    def get_to_version(self) -> str:
        """
        Get the short platform version the tests upgrade to.

        Returns:
            str: the target platform version, for example "26.10".

        """
        return self.to_version

    def get_app_name(self, app_key: str) -> str:
        """
        Get the platform application name for a configured application.

        Args:
            app_key(str): the configured application key.

        Returns:
            str: the application name as the platform reports it.

        Raises:
            ValueError: when the application is not configured.

        """
        return self._get_app(app_key)["app_name"]

    def get_namespace(self, app_key: str) -> str:
        """
        Get the namespace an application runs in.

        Args:
            app_key(str): the configured application key.

        Returns:
            str: the application namespace.

        Raises:
            ValueError: when the application is not configured.

        """
        return self._get_app(app_key)["namespace"]

    def _get_app(self, app_key: str) -> dict:
        """
        Return the configuration block for an application.

        Args:
            app_key(str): the configured application key.

        Returns:
            dict: the application's configuration.

        Raises:
            ValueError: when the application is not configured.

        """
        if app_key not in self.applications:
            raise ValueError(
                f"Application {app_key!r} is not in the application upgrade compatibility config; "
                f"configured applications: {sorted(self.applications)}"
            )
        return self.applications[app_key]

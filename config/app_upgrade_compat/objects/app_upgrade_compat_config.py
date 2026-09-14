import json5


class AppUpgradeCompatConfig:
    """
    This class holds the release data for application platform-upgrade compatibility tests.

    It carries data only: the release being upgraded to, and the application version to expect on a
    given release. What a test does with that data - which steps it runs, what it asserts, which
    phases it checks - lives in the test case, not here.
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

    def get_app_names(self) -> list[str]:
        """
        Get the keys of the applications the configuration carries data for.

        Returns:
            list[str]: the configured application keys.

        """
        return list(self.applications.keys())

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

    def get_app_version(self, app_key: str, release: str) -> str:
        """
        Get the application version to expect on a given platform release.

        The value is a release prefix rather than a full version, because it is matched by
        containment: build suffixes move between respins, so pinning one fails a baseline check on
        a freshly reinstalled lab.

        Args:
            app_key(str): the configured application key.
            release(str): the short platform release, for example "26.03".

        Returns:
            str: the version prefix to expect, for example "26.03-".

        Raises:
            ValueError: when the application is not configured, or has no version for the release.

        """
        versions = self._get_app(app_key).get("versions", {})
        if release not in versions:
            raise ValueError(
                f"Application {app_key!r} has no configured version for release {release!r}; "
                f"configured releases: {sorted(versions)}"
            )
        return versions[release]

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

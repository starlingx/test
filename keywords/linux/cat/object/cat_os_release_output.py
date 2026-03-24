from typing import Union
from keywords.linux.cat.object.cat_os_release_object import CatOSReleaseObject


class CatOSReleaseOutput:
    """A class to interact with and retrieve information from /etc/os-release output.

    This class provides methods to parse and access OS release information
    from the cat /etc/os-release command output.
    """

    def __init__(self, cat_os_release_output: Union[str, list[str]]):
        """Constructor.

        Args:
            cat_os_release_output (Union[str, list[str]]): Raw output from running cat /etc/os-release command.
        """
        self.os_release_object = self._parse_os_release_output(cat_os_release_output)
        self.raw_output = cat_os_release_output

    def _parse_os_release_output(self, output: Union[str, list[str]]) -> CatOSReleaseObject:
        """Parse the raw os-release output into a structured object.

        Args:
            output (Union[str, list[str]]): Raw output from cat /etc/os-release

        Returns:
            CatOSReleaseObject: Parsed OS release information
        """
        os_release = CatOSReleaseObject()
        
        # Convert to list if string
        if isinstance(output, str):
            lines = output.strip().split('\n')
        else:
            lines = output

        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                # Remove quotes from value
                value = value.strip('"\'')
                
                if key == 'NAME':
                    os_release.set_name(value)
                elif key == 'VERSION':
                    os_release.set_version(value)
                elif key == 'ID':
                    os_release.set_id(value)
                elif key == 'ID_LIKE':
                    os_release.set_id_like(value)
                elif key == 'VERSION_ID':
                    os_release.set_version_id(value)
                elif key == 'VERSION_CODENAME':
                    os_release.set_version_codename(value)
                elif key == 'PRETTY_NAME':
                    os_release.set_pretty_name(value)
                elif key == 'ANSI_COLOR':
                    os_release.set_ansi_color(value)
                elif key == 'HOME_URL':
                    os_release.set_home_url(value)
                elif key == 'SUPPORT_URL':
                    os_release.set_support_url(value)
                elif key == 'BUG_REPORT_URL':
                    os_release.set_bug_report_url(value)
                elif key == 'PRIVACY_POLICY_URL':
                    os_release.set_privacy_policy_url(value)
        
        return os_release

    def get_os_release(self) -> CatOSReleaseObject:
        """Get the parsed OS release object.

        Returns:
            CatOSReleaseObject: Parsed OS release information
        """
        return self.os_release_object

    def get_raw_output(self) -> Union[str, list[str]]:
        """Get the raw output from cat /etc/os-release.

        Returns:
            Union[str, list[str]]: Raw command output
        """
        return self.raw_output

    def get_name(self) -> str:
        """Get OS name.

        Returns:
            str: OS name
        """
        return self.os_release_object.get_name()

    def get_version(self) -> str:
        """Get OS version.

        Returns:
            str: OS version
        """
        return self.os_release_object.get_version()

    def get_id(self) -> str:
        """Get OS ID.

        Returns:
            str: OS ID
        """
        return self.os_release_object.get_id()

    def get_version_id(self) -> str:
        """Get OS version ID.

        Returns:
            str: OS version ID
        """
        return self.os_release_object.get_version_id()

    def get_pretty_name(self) -> str:
        """Get pretty formatted name.

        Returns:
            str: Pretty formatted name
        """
        return self.os_release_object.get_pretty_name()

    def get_ansi_color(self) -> str:
        """Get ANSI color.

        Returns:
            str: ANSI color value
        """
        return self.os_release_object.get_ansi_color()

    def get_home_url(self) -> str:
        """Get home URL.

        Returns:
            str: Home URL value
        """
        return self.os_release_object.get_home_url()

    def get_support_url(self) -> str:
        """Get support URL.

        Returns:
            str: Support URL value
        """
        return self.os_release_object.get_support_url()

    def get_bug_report_url(self) -> str:
        """Get bug report URL.

        Returns:
            str: Bug report URL value
        """
        return self.os_release_object.get_bug_report_url()

    def get_id_like(self) -> str:
        """Get ID_LIKE.

        Returns:
            str: ID_LIKE value
        """
        return self.os_release_object.get_id_like()

    def get_version_codename(self) -> str:
        """Get version codename.

        Returns:
            str: Version codename value
        """
        return self.os_release_object.get_version_codename()

    def get_privacy_policy_url(self) -> str:
        """Get privacy policy URL.

        Returns:
            str: Privacy policy URL value
        """
        return self.os_release_object.get_privacy_policy_url()
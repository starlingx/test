"""Onsite Restore configuration module.

Holds the configuration for the "onsite restore without reinstall" flow: the seed
ISO staging locations, the SSL CA cert and HTTPS port used when staging/mounting
the seed, and the resolution of the prebuilt nocloud-factory-install tarball URL
from the unified release point.
"""

from typing import Dict

# URL templates for the unified release point.
# Onsite restore without reinstall is a trixie/master-only feature, so only the
# trixie path layout is templated. The bullseye release tarballs do not contain
# the onsite-restore scripts. If the feature is ever shipped on a bullseye line,
# add a "bullseye" template here and a matching versions entry in the JSON5.
#   trixie: {base}/{branch}/trixie/amd64/wrcp-trixie-{branch}-debian/latest_build/export/windshare/{tarfile}
URL_TEMPLATES = {
    "trixie": "{base}/{branch}/trixie/amd64/wrcp-trixie-{branch}-debian/latest_build/export/windshare/{tarfile}",
}


class OnsiteRestoreConfig:
    """Configuration for the onsite restore without reinstall flow."""

    def __init__(self, onsite_restore_dict: dict):
        """Initialize onsite restore configuration from config dictionary.

        Args:
            onsite_restore_dict (dict): The 'onsite_restore' section from the
                backup_restore JSON5 configuration.
        """
        self.seed_stage_path = onsite_restore_dict.get("seed_stage_path", "/home/sysadmin/onsite-restore-seed")
        self.www_iso_base_path = onsite_restore_dict.get("www_iso_base_path", "/var/www/pages/iso")
        self.sc_https_iso_port = onsite_restore_dict.get("sc_https_iso_port", 8443)
        self.ssl_ca_cert_name = onsite_restore_dict.get("ssl_ca_cert_name", "")
        self.default_restore_timeout = onsite_restore_dict.get("default_restore_timeout", 5400)
        self.release_base_url = onsite_restore_dict.get("release_base_url", "")
        self.nocloud_tarball_name = onsite_restore_dict.get("nocloud_tarball_name", "nocloud-factory-install.tar")
        self.versions = onsite_restore_dict.get("versions", {})

    def get_seed_stage_path(self) -> str:
        """Get the System Controller working directory for seed assembly.

        Returns:
            str: Base path where the nocloud tree is downloaded and the seed ISO
                is assembled (per subcloud a '<subcloud_name>' subdir is used).
        """
        return self.seed_stage_path

    def get_www_iso_base_path(self) -> str:
        """Get the base path of the SC HTTPS-served ISO tree.

        Returns:
            str: Base path; the seed is staged under
                '<www_iso_base_path>/<sw_version>/nodes/<subcloud_name>/seed.iso'.
        """
        return self.www_iso_base_path

    def get_sc_https_iso_port(self) -> int:
        """Get the HTTPS port the System Controller serves staged ISOs on.

        Returns:
            int: HTTPS port used in the staged seed ISO URL.
        """
        return self.sc_https_iso_port

    def get_ssl_ca_cert_name(self) -> str:
        """Get the SSL CA certificate filename to ship in the seed config.

        The onsite-restore seed scripts treat ssl_ca_cert as optional: when this is
        empty the cert is neither staged nor referenced, and the restore proceeds
        without installing a CA cert. When set, the named cert must be present on
        the System Controller home directory so it can be staged into the seed.

        Returns:
            str: Cert filename, or an empty string when no cert is configured.
        """
        return self.ssl_ca_cert_name

    def get_default_restore_timeout(self) -> int:
        """Get the default restore monitoring timeout.

        Returns:
            int: Timeout in seconds for the restore monitoring phase.
        """
        return self.default_restore_timeout

    def get_release_base_url(self) -> str:
        """Get the unified release point base URL.

        Returns:
            str: Base URL for tarball resolution, or an empty string when not
                configured (a non-public config file must supply the real value).
        """
        return self.release_base_url

    def get_nocloud_tarball_name(self) -> str:
        """Get the nocloud-factory-install tarball filename.

        Returns:
            str: Tarball filename (e.g. 'nocloud-factory-install.tar').
        """
        return self.nocloud_tarball_name

    def get_available_versions(self) -> list:
        """Get the list of software versions configured in the versions registry.

        Returns:
            list: Available software version keys (e.g. ['26.10', '26.03', ...]).
        """
        return list(self.versions.keys())

    def resolve_nocloud_tarball_url(self, software_version: str) -> str:
        """Resolve the full download URL for the nocloud tarball of a version.

        The subcloud software version is matched against the versions registry by
        prefix (e.g. a reported '26.10-90' resolves the '26.10' entry), so a build
        suffix does not need to be pinned. If the matched entry provides an explicit
        'tarball_url', that value is returned as-is. Otherwise the URL is constructed
        from the release base URL, the entry's branch, and the distro template.

        Args:
            software_version (str): The subcloud software version reported by
                dcmanager (e.g. '26.10' or '26.10-90').

        Returns:
            str: Full HTTP URL to download the nocloud-factory-install tarball.

        Raises:
            KeyError: If no versions registry entry matches the software version.
            ValueError: If the matched entry has no explicit tarball_url and no
                release_base_url is configured to build one from.
        """
        version_entry = self._match_version_entry(software_version)

        explicit_url = version_entry.get("tarball_url", "")
        if explicit_url:
            return explicit_url

        if not self.release_base_url:
            raise ValueError("onsite_restore release_base_url is not configured; supply a backup_restore config file " "(--backup_restore_config_file) with a release_base_url, or an explicit per-version tarball_url.")

        distro = version_entry.get("distro", "trixie")
        branch = version_entry.get("branch", "master")
        template = URL_TEMPLATES.get(distro, URL_TEMPLATES["trixie"])
        return template.format(
            base=self.release_base_url,
            branch=branch,
            tarfile=self.nocloud_tarball_name,
        )

    def _match_version_entry(self, software_version: str) -> Dict[str, str]:
        """Match a software version to a versions registry entry by prefix.

        An exact key match wins first. Otherwise the registry keys are tried
        longest-first so the most specific prefix wins; this avoids an ambiguous
        match when one key is a string-prefix of another (e.g. '26.1' vs '26.10'
        for a reported '26.10-90', which must resolve to '26.10').

        Args:
            software_version (str): The subcloud software version (may include a
                build suffix such as '26.10-90').

        Returns:
            Dict[str, str]: The matched version entry ({'branch', 'distro', ...}).

        Raises:
            KeyError: If no configured version is a prefix of software_version.
        """
        if software_version in self.versions:
            return self.versions[software_version]
        for version_key in sorted(self.versions, key=len, reverse=True):
            if software_version.startswith(version_key):
                return self.versions[version_key]
        raise KeyError(f"No onsite_restore versions entry matches software version " f"'{software_version}'. Available: {list(self.versions.keys())}")

    def __str__(self) -> str:
        """Return a human-readable representation of the configuration.

        Returns:
            str: Summary of the onsite restore configuration.
        """
        return f"OnsiteRestoreConfig(seed_stage_path={self.seed_stage_path}, " f"www_iso_base_path={self.www_iso_base_path}, " f"default_restore_timeout={self.default_restore_timeout}, " f"release_base_url={self.release_base_url}, " f"nocloud_tarball_name={self.nocloud_tarball_name}, " f"versions={list(self.versions.keys())})"

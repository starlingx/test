"""Unit tests for relative major-release lookup in CloudPlatformVersionManagerClass."""

import unittest

from keywords.cloud_platform.version_info.cloud_platform_software_version import CloudPlatformSoftwareVersion
from keywords.cloud_platform.version_info.cloud_platform_version_manager import UNKNOWN_VERSION_ID, CloudPlatformVersionManagerClass
from keywords.python.product_version import ProductVersion


class VersionManagerWithFixedRunningVersion(CloudPlatformVersionManagerClass):
    """Version manager whose running version is supplied instead of read from a system.

    Overrides the single method that performs the isystems API call so the
    relative-lookup logic can be exercised without a live lab.
    """

    def __init__(self, running_version: ProductVersion):
        """Constructor.

        Args:
            running_version (ProductVersion): Version to report as running.
        """
        super().__init__()
        self.running_version = running_version

    def _get_sw_version_from_system(self) -> ProductVersion:
        """Return the injected running version instead of querying a system.

        Returns:
            ProductVersion: The version supplied to the constructor.
        """
        return self.running_version


class TestGetAllProductVersions(unittest.TestCase):
    """Test suite for CloudPlatformVersionManagerClass.get_all_product_versions."""

    def test_versions_are_sorted_oldest_first(self):
        """Verify declared versions come back ordered by ascending version id."""
        versions = CloudPlatformVersionManagerClass().get_all_product_versions()

        version_ids = [version.get_id() for version in versions]
        self.assertEqual(version_ids, sorted(version_ids))

    def test_includes_declared_versions(self):
        """Verify the newest and oldest declared releases are both present."""
        version_names = [version.get_name() for version in CloudPlatformVersionManagerClass().get_all_product_versions()]

        self.assertIn(CloudPlatformSoftwareVersion.STARLINGX_7_0.get_name(), version_names)
        self.assertIn(CloudPlatformSoftwareVersion.STARLINGX_13_0.get_name(), version_names)


class TestGetMajorReleaseRelative(unittest.TestCase):
    """Test suite for CloudPlatformVersionManagerClass.get_major_release_relative."""

    def test_zero_releases_back_is_running_version(self):
        """Verify an offset of zero resolves to the running release."""
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_13_0)

        self.assertEqual(manager.get_major_release_relative(0), CloudPlatformSoftwareVersion.STARLINGX_13_0)

    def test_one_release_back_from_newest(self):
        """Verify N-1 steps back exactly one declared release."""
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_13_0)

        self.assertEqual(manager.get_major_release_relative(1), CloudPlatformSoftwareVersion.STARLINGX_12_0)

    def test_two_releases_back_from_newest(self):
        """Verify N-2 steps back exactly two declared releases."""
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_13_0)

        self.assertEqual(manager.get_major_release_relative(2), CloudPlatformSoftwareVersion.STARLINGX_11_0)

    def test_offset_tracks_running_version(self):
        """Verify the same offset resolves differently as the running version changes.

        This is the behaviour the hardcoded getters could not provide: on an
        older running release, N-1 must resolve to that release's predecessor.
        """
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_11_0)

        self.assertEqual(manager.get_major_release_relative(1), CloudPlatformSoftwareVersion.STARLINGX_10_0)

    def test_negative_offset_raises(self):
        """Verify a negative offset is rejected rather than silently wrapping."""
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_13_0)

        with self.assertRaises(ValueError):
            manager.get_major_release_relative(-1)

    def test_offset_before_oldest_release_raises(self):
        """Verify stepping back past the oldest declared release raises."""
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_7_0)

        with self.assertRaises(ValueError):
            manager.get_major_release_relative(1)

    def test_undeclared_running_version_raises(self):
        """Verify a running version absent from the enumeration raises.

        An undeclared version is assigned UNKNOWN_VERSION_ID, which has no
        meaningful position in the release order, so relative lookup against it
        must fail loudly instead of returning a wrong release.
        """
        manager = VersionManagerWithFixedRunningVersion(ProductVersion("99.99", UNKNOWN_VERSION_ID))

        with self.assertRaises(ValueError):
            manager.get_major_release_relative(1)


class TestMajorReleaseAccessors(unittest.TestCase):
    """Test suite for the named major-release accessors."""

    def setUp(self):
        """Set up a manager running the newest declared release."""
        self.manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_13_0)

    def test_last_major_release_is_one_back(self):
        """Verify get_last_major_release delegates to an offset of one."""
        self.assertEqual(self.manager.get_last_major_release(), self.manager.get_major_release_relative(1))

    def test_second_last_major_release_is_two_back(self):
        """Verify get_second_last_major_release delegates to an offset of two."""
        self.assertEqual(self.manager.get_second_last_major_release(), self.manager.get_major_release_relative(2))

    def test_third_last_major_release_is_three_back(self):
        """Verify get_third_last_major_release delegates to an offset of three."""
        self.assertEqual(self.manager.get_third_last_major_release(), self.manager.get_major_release_relative(3))


class TestResolveReleaseToken(unittest.TestCase):
    """Test suite for CloudPlatformVersionManagerClass.resolve_release_token."""

    def setUp(self):
        """Set up a manager running the newest declared release."""
        self.manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_13_0)

    def test_none_returns_none(self):
        """Verify a missing token resolves to None."""
        self.assertIsNone(self.manager.resolve_release_token(None))

    def test_n_resolves_to_running_version(self):
        """Verify 'N' resolves to the running release."""
        self.assertEqual(self.manager.resolve_release_token("N"), CloudPlatformSoftwareVersion.STARLINGX_13_0.get_name())

    def test_n_minus_1_resolves_to_previous_release(self):
        """Verify 'N-1' resolves to the release before the running one."""
        self.assertEqual(self.manager.resolve_release_token("N-1"), CloudPlatformSoftwareVersion.STARLINGX_12_0.get_name())

    def test_n_minus_2_resolves_to_two_releases_back(self):
        """Verify 'N-2' resolves to two releases before the running one."""
        self.assertEqual(self.manager.resolve_release_token("N-2"), CloudPlatformSoftwareVersion.STARLINGX_11_0.get_name())

    def test_explicit_version_passes_through(self):
        """Verify an explicit version string is returned unchanged."""
        self.assertEqual(self.manager.resolve_release_token("24.09"), "24.09")

    def test_n_minus_1_on_older_running_version(self):
        """Verify 'N-1' follows the running version rather than a fixed release."""
        manager = VersionManagerWithFixedRunningVersion(CloudPlatformSoftwareVersion.STARLINGX_11_0)

        self.assertEqual(manager.resolve_release_token("N-1"), CloudPlatformSoftwareVersion.STARLINGX_10_0.get_name())


if __name__ == "__main__":
    unittest.main()

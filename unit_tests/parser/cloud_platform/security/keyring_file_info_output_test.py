"""Unit tests for KeyringFileInfo and KeyringFileInfoOutput."""

from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info import KeyringFileInfo
from keywords.cloud_platform.security.luks_keyring.objects.keyring_file_info_output import KeyringFileInfoOutput


def test_keyring_file_info_basic():
    """Tests basic file info parsing."""
    info = KeyringFileInfo(
        owner="root",
        group="sys_protected",
        permissions="640",
        path="/var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/.keyring_secret",
    )

    assert info.get_owner() == "root"
    assert info.get_group() == "sys_protected"
    assert info.get_permissions() == "640"
    assert info.has_world_access() is False


def test_keyring_file_info_world_readable():
    """Tests detection of world-readable permissions."""
    info = KeyringFileInfo(owner="root", group="root", permissions="644", path="/tmp/test")
    assert info.has_world_access() is True


def test_keyring_file_info_no_world_access():
    """Tests various non-world-accessible permissions."""
    for perm in ["600", "640", "660", "700", "750"]:
        info = KeyringFileInfo(owner="root", group="sys_protected", permissions=perm, path="/tmp/test")
        assert info.has_world_access() is False, f"Permission {perm} should not have world access"


def test_keyring_file_info_output_single_line():
    """Tests output parser with single stat line."""
    output = ["640 root sys_protected /var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/.keyring_secret"]
    parsed = KeyringFileInfoOutput(output)
    files = parsed.get_files()

    assert len(files) == 1
    assert files[0].get_permissions() == "640"
    assert files[0].get_owner() == "root"
    assert files[0].get_group() == "sys_protected"
    assert files[0].has_world_access() is False


def test_keyring_file_info_output_multiple_lines():
    """Tests output parser with multiple stat lines."""
    output = [
        "640 root sys_protected /var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/.keyring_secret",
        "640 root sys_protected /var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/crypted_pass.cfg",
        "770 root sys_protected /var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/keyringlock",
    ]
    parsed = KeyringFileInfoOutput(output)
    files = parsed.get_files()

    assert len(files) == 3
    secret = parsed.get_file("/var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/.keyring_secret")
    assert secret is not None
    assert secret.get_permissions() == "640"


def test_keyring_file_info_output_empty():
    """Tests output parser with empty input."""
    parsed = KeyringFileInfoOutput([])
    assert len(parsed.get_files()) == 0


def test_keyring_file_info_output_get_file_not_found():
    """Tests get_file returns None for non-existent path."""
    output = ["640 root sys_protected /var/luks/stx/luks_fs/controller/.keyring/26.10/python_keyring/.keyring_secret"]
    parsed = KeyringFileInfoOutput(output)
    assert parsed.get_file("/nonexistent") is None

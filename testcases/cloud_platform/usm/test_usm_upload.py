"""
Basic USM Upload Tests (Foundation Layer)
=========================================

This module provides **foundational test coverage** for the USM (Upgrade and Software Management) system,
specifically focusing on uploading software releases and patches. These tests verify that an `.iso` + `.sig`
pair (for major upgrades) or `.patch` file (for patches) can be uploaded successfully to a StarlingX controller
and reach the "available" state.

Scope:
------
These tests are **intentionally minimal** and serve as a starting point. They do not implement full
end-to-end upgrade or patch deployment flows. Their goal is to validate:

- Configuration parsing via `UsmConfig`.
- Optional remote-to-local file copy using `rsync` via `FileKeywords`.
- Uploading files via the `software upload` or `software upload-dir` CLI.
- Polling for availability using `software show`.

Key Concepts:
-------------
- The config file is parsed using `ConfigurationManager.get_usm_config()` and provides:
  - ISO/SIG/PATCH paths (`get_iso_path()`, `get_sig_path()`, `get_patch_path()`).
  - Destination and expected release ID (`get_to_release_ids()`).
  - Upload timeouts and polling intervals.

- If `copy_from_remote` is `True`, contributors should use
  `FileKeywords(ssh_connection).copy_from_remote(remote_path, local_path, ...)`
  to retrieve the necessary `.iso`, `.sig`, or `.patch` files from a remote server
  before calling the upload keyword. This supports workflows where files are staged
  on build hosts or CI/CD artifacts servers.

How to Extend:
--------------
This module is meant to be built upon. Contributors are encouraged to:
- Validate `software list` and `software show` parsing logic.
- Chain upload -> deploy precheck -> deploy start -> deploy complete steps for full upgrade flows.
- Cover patch rollback, deploy delete, and state recovery.

Location of Supporting Logic:
-----------------------------
- Upload Keywords: `keywords/cloud_platform/upgrade/usm_keywords.py`.
  - Contains `upload_patch_file()`, `upload_release()`, and verification methods that call `software show`.
- Release State Polling: `keywords/cloud_platform/upgrade/software_show_keywords.py`.
  - Wraps `software show` and extracts release state (e.g., `"available"`).
- Config Management: `config/usm/objects/usm_config.py`.
  - Parses structured JSON5 configuration and validates upgrade parameters.
- Remote Copy Support: `keywords/files/file_keywords.py`.
  - Implements `copy_from_remote()` for fetching `.iso`, `.sig`, or `.patch` files using `rsync`.

These tests form a solid base for contributors to validate the upload mechanism
before tackling the broader USM lifecycle.
"""

from config.configuration_manager import ConfigurationManager
from framework.logging.automation_logger import get_logger
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.cloud_platform.upgrade.usm_keywords import USMKeywords


def test_usm_upload_release_from_local():
    """
    Upload a USM ISO already present on the controller and verify the upload was successful.

    Assumes that:
    - ISO and SIG files are already present at the expected paths.
    - No remote copy is required (copy_from_remote is False).
    - The release ID is known and matches the ISO being uploaded.
    """
    get_logger().log_info("Starting local upload test for USM release ISO.")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    usm_keywords = USMKeywords(ssh_connection)
    usm_config = ConfigurationManager.get_usm_config()

    iso_path = usm_config.get_iso_path()
    sig_path = usm_config.get_sig_path()
    release_id = usm_config.get_to_release_ids()[0]
    timeout = usm_config.get_upload_timeout_sec()
    poll_interval = usm_config.get_upload_poll_interval_sec()

    get_logger().log_test_case_step(f"Uploading software release: ISO={iso_path}, SIG={sig_path}")

    usm_keywords.upload_and_verify_release(
        iso_path=iso_path,
        sig_path=sig_path,
        expected_release_id=release_id,
        timeout=timeout,
        poll_interval=poll_interval,
    )

    get_logger().log_info(f"Upload verification complete for release: {release_id}")


def test_usm_upload_patch_from_local():
    """
    Upload a USM patch file already present on the controller and verify it becomes available.

    Assumes that:
    - The patch file is already located at the configured path.
    - No remote copy is required (copy_from_remote is False).
    - The expected release ID after applying the patch is known.
    """
    get_logger().log_info("Starting local upload test for USM patch file.")

    ssh_connection = LabConnectionKeywords().get_active_controller_ssh()
    usm_keywords = USMKeywords(ssh_connection)
    usm_config = ConfigurationManager.get_usm_config()

    patch_file_path = usm_config.get_patch_path()
    expected_release_id = usm_config.get_to_release_ids()[0]
    timeout = usm_config.get_upload_timeout_sec()
    poll_interval = usm_config.get_upload_poll_interval_sec()

    get_logger().log_test_case_step(f"Uploading patch file: {patch_file_path}")

    usm_keywords.upload_and_verify_patch_file(
        patch_file_path=patch_file_path,
        expected_release_id=expected_release_id,
        timeout=timeout,
        poll_interval=poll_interval,
    )

    get_logger().log_info(f"Upload verification complete for patch release: {expected_release_id}")

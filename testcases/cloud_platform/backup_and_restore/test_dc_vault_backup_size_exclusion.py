"""Central Controller backup dc-vault size estimate must honour exclude_dirs.

Behaviour under test:
    On a Distributed Cloud System Controller, the platform backup playbook runs a
    free-space pre-check before archiving. It estimates the required archive size and
    fails the backup if the destination partition is smaller than that estimate. The
    dc-vault size estimate must apply the same ``--exclude`` list as the archive step, so
    that a directory placed in ``exclude_dirs`` is excluded from BOTH the archive and the
    size estimate. If the estimate ignored the exclusions it would be inflated and could
    fail the backup on a destination that the real archive would fit into.

    This test verifies, directly from the ansible ``-vv`` log, that the dc-vault size
    estimate excludes the excluded directory and that the resulting estimate fits the
    (deliberately constrained) destination.
"""

from pytest import FixtureRequest, mark

from framework.logging.automation_logger import get_logger
from framework.validation.validation import fail, validate_equals, validate_greater_than, validate_less_than_or_equal, validate_str_contains
from keywords.cloud_platform.ansible_playbook.ansible_playbook_keywords import AnsiblePlaybookKeywords
from keywords.cloud_platform.health.health_keywords import HealthKeywords
from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords
from keywords.files.file_keywords import FileKeywords
from keywords.linux.df.df_keywords import DfKeywords

# --- Module-level constants ---
# The platform backup is always written under /opt/platform-backup/localhost, which lives
# on the /opt/platform-backup filesystem; the free-space pre-check is measured there.
# NOTE: /opt/platform-backup/localhost may not exist until a backup is triggered, so
# filesystem queries (df) must target the parent path that is always present.
BACKUP_DIR = "/opt/platform-backup/localhost"
BACKUP_FILESYSTEM_PATH = "/opt/platform-backup"
BACKUP_MOUNT_POINT = "/var/rootdirs/opt/platform-backup"
DC_VAULT_PERMDIR = "/opt/dc-vault"
# The dc-vault subcloud-backup directory. This is the directory the platform recommends
# excluding from a System Controller backup (it holds large subcloud backups) and is a
# valid exclude_dirs value. The test excludes this whole directory and seeds its dummy
# content inside it, so the produced dc-vault archive stays small and the scenario mirrors
# excluding real subcloud-backup content — without depending on a subcloud being installed.
DC_VAULT_EXCLUDE_DIR = "/opt/dc-vault/backups"
DC_VAULT_SEED_DIR = "/opt/dc-vault/backups/backup-size-exclusion-seed"
DC_VAULT_SEED_FILE = "/opt/dc-vault/backups/backup-size-exclusion-seed/seed.img"
BACKUP_FILLER_DIR = "/opt/platform-backup/backup-size-exclusion-filler"
BACKUP_FILLER_FILE = "/opt/platform-backup/backup-size-exclusion-filler/filler.img"
# Size of the excludable dc-vault content the test seeds; large enough to be a
# meaningful lever on the size estimate.
SEED_SIZE_KIB = 2 * 1024 * 1024  # 2 GiB
# Allowance for the platform (non-dc-vault) portion of the estimate; the dc-vault
# contribution dominates but the platform dirs add a small amount on top.
PLATFORM_ALLOWANCE_KIB = 1024 * 1024  # 1 GiB
# Never drive the backup filesystem below this free space with the filler.
SAFETY_FLOOR_KIB = 1024 * 1024  # 1 GiB
# Headroom added on top of the (seed-excluded) estimate so the fixed backup comfortably
# fits. Must be smaller than SEED_SIZE_KIB so that counting the seed would tip it over.
BAND_MARGIN_KIB = 512 * 1024  # 0.5 GiB


def _compute_filler_size_kib(available_kib: int, seed_excluded_estimate_kib: int, seed_size_kib: int) -> int:
    """Compute the filler size that places free space inside the straddle band.

    The goal is to constrain ``available`` in the backup directory so that:

        seed_excluded_estimate  <  available_after_fill  <  seed_excluded_estimate + seed_size

    i.e. the backup fits when the seed is excluded from the estimate (correct behaviour),
    but would not fit if the seed were counted. We target free space a small margin above
    the seed-excluded estimate, then clamp so we never allocate a negative size and never
    breach the safety floor.

    Args:
        available_kib (int): Current free space in the backup directory (KiB).
        seed_excluded_estimate_kib (int): Estimated required size with the seed excluded (KiB).
        seed_size_kib (int): Size of the seeded excludable directory (KiB).

    Returns:
        int: Filler size in KiB (0 if no filler is needed or possible).
    """
    # Sit BAND_MARGIN_KIB above the seed-excluded estimate: the fixed backup fits, and
    # adding the seed (seed_size_kib > BAND_MARGIN_KIB) would exceed available space.
    target_available_kib = seed_excluded_estimate_kib + BAND_MARGIN_KIB
    filler_kib = available_kib - target_available_kib
    # Respect the safety floor: never reduce free space below SAFETY_FLOOR_KIB.
    max_filler_kib = available_kib - SAFETY_FLOOR_KIB
    if filler_kib > max_filler_kib:
        filler_kib = max_filler_kib
    if filler_kib < 0:
        filler_kib = 0
    get_logger().log_info(f"Filler sizing: available={available_kib} seed_excluded_estimate={seed_excluded_estimate_kib} seed_size={seed_size_kib} target_available={target_available_kib} filler={filler_kib}")
    return filler_kib


@mark.p2
@mark.lab_has_standby_controller
def test_dc_vault_backup_size_estimate_excludes_exclude_dirs(request: FixtureRequest):
    """Verify the dc-vault backup size estimate applies exclude_dirs.

    Runs on any Distributed Cloud system controller; it does not require a subcloud to be
    installed. The test seeds its own content inside the dc-vault backups directory and
    excludes that directory, so the scenario mirrors excluding real subcloud-backup content
    while staying deterministic regardless of what subcloud backups currently exist.

    Test Steps:
        - Seed a known-size dummy file inside the dc-vault backups directory.
        - Read live free space in the backup directory and the dc-vault sizes.
        - Constrain the backup directory's free space (fallocate filler) so the excluded
          dc-vault content would tip the estimate over the available space if it were counted.
        - Run the platform backup with -vv, excluding the dc-vault backups directory.
        - From the ansible log, verify the dc-vault du applied --exclude for the excluded dir.
        - Verify the playbook's dc-vault size matches an independent du with the same exclusion.
        - Verify the estimate fits the constrained free space, but would NOT fit if the
          excluded content were counted.
        - Verify the free-space pre-check passed and the produced archive excludes the dir.

    Teardown:
        - Delete the seeded content, the filler, and any produced backup tarballs;
          validate free space is restored.
    """
    central_ssh = LabConnectionKeywords().get_active_controller_ssh()
    file_keywords = FileKeywords(central_ssh)
    df_keywords = DfKeywords(central_ssh)
    ansible_keywords = AnsiblePlaybookKeywords(central_ssh)

    get_logger().log_info("Validating cluster health before backup")
    HealthKeywords(central_ssh).validate_healty_cluster()

    baseline_available_kib = df_keywords.get_disk_usage(BACKUP_FILESYSTEM_PATH).get_df_by_mount_point(BACKUP_MOUNT_POINT).get_available_kb()

    # Register cleanup BEFORE creating anything so the seed and filler are always removed.
    def teardown():
        get_logger().log_info("Teardown: removing seeded dc-vault content, filler, and any produced backup tarballs")
        file_keywords.delete_folder_with_sudo(DC_VAULT_SEED_DIR)
        file_keywords.delete_folder_with_sudo(BACKUP_FILLER_DIR)
        # The System Controller backup produces both a platform (*_platform_backup_*.tgz)
        # and a dc-vault (*_dc_vault_backup_*.tgz) archive; remove any of both.
        # BACKUP_DIR may not exist if the backup was never triggered; guard the listing.
        if file_keywords.file_exists(BACKUP_DIR):
            for backup_file in file_keywords.get_files_in_dir(BACKUP_DIR, is_sudo=True):
                if backup_file.endswith(".tgz") and ("_platform_backup_" in backup_file or "_dc_vault_backup_" in backup_file):
                    file_keywords.delete_file(f"{BACKUP_DIR}/{backup_file}")
        restored_available_kib = df_keywords.get_disk_usage(BACKUP_FILESYSTEM_PATH).get_df_by_mount_point(BACKUP_MOUNT_POINT).get_available_kb()
        get_logger().log_info(f"Teardown: restored available={restored_available_kib}KiB (baseline was {baseline_available_kib}KiB)")

    request.addfinalizer(teardown)

    # Seed a known-size dummy file inside the dc-vault backups directory so the scenario
    # does not depend on any pre-existing subcloud backups. The whole backups directory is
    # what gets excluded, mirroring excluding real subcloud-backup content.
    get_logger().log_info(f"Seeding {SEED_SIZE_KIB}KiB of content into {DC_VAULT_SEED_DIR} (excluded via {DC_VAULT_EXCLUDE_DIR})")
    file_keywords.create_directory_with_sudo(DC_VAULT_SEED_DIR)
    df_keywords.allocate_disk_space_kb(SEED_SIZE_KIB, DC_VAULT_SEED_FILE, is_sudo=True)

    # Measure free space and dc-vault sizes (independent ground truth) after seeding.
    dc_vault_full_kib = file_keywords.get_directory_size_kb(DC_VAULT_PERMDIR, is_sudo=True)
    excluded_dir_kib = file_keywords.get_directory_size_kb(DC_VAULT_EXCLUDE_DIR, is_sudo=True)
    dc_vault_excluded_estimate_kib = file_keywords.get_directory_size_kb(DC_VAULT_PERMDIR, exclude_dirs=[DC_VAULT_EXCLUDE_DIR], is_sudo=True)
    get_logger().log_info(f"dc_vault_full={dc_vault_full_kib}KiB, excluded_dir={excluded_dir_kib}KiB, dc_vault_after_exclude={dc_vault_excluded_estimate_kib}KiB")
    validate_greater_than(excluded_dir_kib, SAFETY_FLOOR_KIB, "Excluded dc-vault backups directory is large enough to matter for the size estimate")

    # Re-read available space after seeding, then constrain the backup directory's free
    # space so it sits just above the estimate with the backups directory excluded: the
    # backup fits when excluded, but would not fit if that content were counted.
    available_before_fill_kib = df_keywords.get_disk_usage(BACKUP_FILESYSTEM_PATH).get_df_by_mount_point(BACKUP_MOUNT_POINT).get_available_kb()
    # Include a platform allowance on top of the dc-vault portion; the platform dirs add a
    # small amount to the estimate beyond the (dominant) dc-vault contribution.
    seed_excluded_estimate_kib = dc_vault_excluded_estimate_kib + PLATFORM_ALLOWANCE_KIB
    filler_kib = _compute_filler_size_kib(available_before_fill_kib, seed_excluded_estimate_kib, excluded_dir_kib)
    if filler_kib <= 0:
        fail(f"Cannot constrain {BACKUP_DIR}: available {available_before_fill_kib}KiB is too small relative to the excluded estimate {seed_excluded_estimate_kib}KiB and the safety floor to build a valid straddle band")

    file_keywords.create_directory_with_sudo(BACKUP_FILLER_DIR)
    df_keywords.allocate_disk_space_kb(filler_kib, BACKUP_FILLER_FILE, is_sudo=True)

    constrained_available_kib = df_keywords.get_disk_usage(BACKUP_FILESYSTEM_PATH).get_df_by_mount_point(BACKUP_MOUNT_POINT).get_available_kb()
    get_logger().log_info(f"Constrained available={constrained_available_kib}KiB after allocating {filler_kib}KiB filler")
    # Confirm the band: with the backups directory excluded the estimate fits, but adding
    # that content would exceed the remaining free space.
    validate_greater_than(constrained_available_kib, seed_excluded_estimate_kib, "Remaining free space is above the estimate with the backups directory excluded")
    validate_greater_than(seed_excluded_estimate_kib + excluded_dir_kib, constrained_available_kib, "Adding the excluded content would exceed remaining free space")

    # Run the backup verbosely, excluding the dc-vault backups directory.
    get_logger().log_info(f"Running platform backup excluding {DC_VAULT_EXCLUDE_DIR}")
    estimation = ansible_keywords.ansible_playbook_backup_with_size_estimation(BACKUP_DIR, exclude_dirs=[DC_VAULT_EXCLUDE_DIR], dc_vault_permdir=DC_VAULT_PERMDIR)

    # The dc-vault du must apply --exclude for the excluded dir.
    validate_equals(estimation.is_dc_vault_exclude_applied(DC_VAULT_EXCLUDE_DIR), True, f"dc-vault du applied --exclude for {DC_VAULT_EXCLUDE_DIR}")
    validate_str_contains(estimation.get_dc_vault_du_command(), f"--exclude '{DC_VAULT_EXCLUDE_DIR}'", "dc-vault du command carries the exclude argument")

    # Calculation correctness: the playbook's dc-vault size equals an independent du with
    # the same exclusion applied.
    playbook_dc_vault_kib = estimation.get_dc_vault_size_kib()
    validate_equals(playbook_dc_vault_kib, dc_vault_excluded_estimate_kib, "Playbook dc-vault size equals independent du with exclusion applied")

    # The estimate must fit the constrained free space, but would NOT fit if the excluded
    # content were counted.
    total_estimate_kib = estimation.get_total_platform_size_estimation()
    log_available_kib = estimation.get_available_disk_size_kib()
    validate_less_than_or_equal(total_estimate_kib, log_available_kib, "Estimated required size fits the available backup space")
    validate_greater_than(total_estimate_kib + excluded_dir_kib, log_available_kib, "Estimate would exceed available space if the excluded content were counted")

    # The free-space pre-check gate must have passed (been skipped).
    validate_equals(estimation.did_space_precheck_pass(), True, "Backup free-space pre-check passed")

    # The produced dc-vault archive must not contain the excluded directory contents.
    dc_vault_tarball = ansible_keywords.get_latest_platform_backup_tarball(BACKUP_DIR, filename_substring="_dc_vault_backup_")
    validate_greater_than(len(dc_vault_tarball), 0, "A dc-vault backup tarball was produced")
    excluded_matches = file_keywords.find_in_tgz(dc_vault_tarball, "backup-size-exclusion-seed", is_sudo=True)
    validate_equals(excluded_matches, 0, "Produced dc-vault backup archive excludes the seeded directory")

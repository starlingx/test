from typing import List

MAX_CONTROL_PLANE_SKEW = 3


def parse_minor_version(version: str) -> int:
    """Extract the minor version number from a Kubernetes version string.

    Args:
        version (str): Kubernetes version string (e.g. 'v1.33.0').

    Returns:
        int: The minor version number.
    """
    return int(version.lstrip("v").split(".")[1])


def build_control_plane_batches(active_version: str, target_version: str, all_versions: List[str]) -> List[List[str]]:
    """Build batches of control-plane upgrade versions respecting the 3-version skew policy.

    Each call to kube_host_upgrade_control_plane upgrades one minor version.
    The control-plane can be at most 3 minor versions ahead of the kubelet,
    so after every 3 control-plane upgrades, kubelets must catch up.

    Example: v1.29 -> v1.33 produces [[v1.30, v1.31, v1.32], [v1.33]]
      - Batch 1: upgrade control-plane to v1.30, v1.31, v1.32, then upgrade kubelets
      - Batch 2: upgrade control-plane to v1.33, then upgrade kubelets

    Args:
        active_version (str): Current active Kubernetes version (e.g. 'v1.29.2').
        target_version (str): Final target Kubernetes version (e.g. 'v1.33.0').
        all_versions (List[str]): All versions from kube-version-list (active + available).

    Returns:
        List[List[str]]: Batches of versions, each batch has at most 3 versions.
    """
    active_minor = parse_minor_version(active_version)
    target_minor = parse_minor_version(target_version)

    versions_by_minor = {}
    for v in all_versions:
        minor = parse_minor_version(v)
        if active_minor < minor <= target_minor:
            if minor not in versions_by_minor or v > versions_by_minor[minor]:
                versions_by_minor[minor] = v

    ordered_versions = [versions_by_minor[m] for m in sorted(versions_by_minor.keys())]

    return [ordered_versions[i : i + MAX_CONTROL_PLANE_SKEW] for i in range(0, len(ordered_versions), MAX_CONTROL_PLANE_SKEW)]


def find_target_beyond_skew(active_version: str, available_versions: List[str]) -> str:
    """Find the first available version that is more than 3 minor versions ahead.

    Args:
        active_version (str): Current active Kubernetes version.
        available_versions (List[str]): Available versions from kube-version-list.

    Returns:
        str: A version that is 4+ minor versions ahead of active.

    Raises:
        ValueError: If no version beyond the skew limit is available.
    """
    active_minor = parse_minor_version(active_version)
    for v in sorted(available_versions, key=parse_minor_version):
        if parse_minor_version(v) - active_minor > MAX_CONTROL_PLANE_SKEW:
            return v
    raise ValueError(f"No available version is more than {MAX_CONTROL_PLANE_SKEW} minor versions " f"ahead of {active_version}. Available: {available_versions}")


def find_target_at_least_two_ahead(active_version: str, available_versions: List[str]) -> str:
    """Find the first available version that is at least 2 minor versions ahead.

    Args:
        active_version (str): Current active Kubernetes version.
        available_versions (List[str]): Available versions from kube-version-list.

    Returns:
        str: A version that is 2+ minor versions ahead of active.

    Raises:
        ValueError: If no version at least 2 minor versions ahead is available.
    """
    active_minor = parse_minor_version(active_version)
    for v in sorted(available_versions, key=parse_minor_version):
        if parse_minor_version(v) - active_minor >= 2:
            return v
    raise ValueError(f"No available version is at least 2 minor versions ahead of " f"{active_version}. Available: {available_versions}")


def find_version_one_before_target(target_version: str, all_versions: List[str]) -> str:
    """Find the available version that is one minor version before the target.

    Args:
        target_version (str): Target Kubernetes version (e.g. 'v1.34.1').
        all_versions (List[str]): All versions from kube-version-list.

    Returns:
        str: The version one minor version before target.

    Raises:
        ValueError: If no version one minor before target is found.
    """
    target_minor = parse_minor_version(target_version)
    for v in all_versions:
        if parse_minor_version(v) == target_minor - 1:
            return v
    raise ValueError(f"No version with minor {target_minor - 1} found. Available: {all_versions}")

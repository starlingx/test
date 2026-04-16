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

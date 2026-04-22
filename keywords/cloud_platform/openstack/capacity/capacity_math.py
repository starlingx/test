"""Pure math helpers for OpenStack capacity calculations."""


def calculate_compute_effective(
    total: int,
    allocation_ratio: float,
    reserved: int,
) -> int:
    """Calculate effective compute capacity considering overcommit and reserves.

    Formula: int(total * allocation_ratio) - reserved

    Args:
        total (int): Total physical capacity (vCPUs, MB, or GB).
        allocation_ratio (float): Overcommit ratio (e.g. 16.0 for CPU).
        reserved (int): System-reserved capacity.

    Returns:
        int: Effective capacity available for allocation.

    Example:
        >>> calculate_compute_effective(126, 16.0, 0)
        2016
        >>> calculate_compute_effective(255360, 1.0, 8000)
        247360
    """
    return int(total * allocation_ratio) - reserved


def calculate_storage_effective(
    total_gb: float,
    over_subscription_ratio: float,
    reserved_percentage: int,
) -> float:
    """Calculate effective storage capacity considering oversubscription and reserves.

    Formula: total * ratio * (1 - reserved_pct / 100)

    Args:
        total_gb (float): Total storage capacity in GB.
        over_subscription_ratio (float): Max oversubscription ratio.
        reserved_percentage (int): Percentage reserved for system use.

    Returns:
        float: Effective storage capacity in GB, rounded to 2 decimals.

    Example:
        >>> calculate_storage_effective(3774.73, 20.0, 0)
        75494.6
        >>> calculate_storage_effective(1000.0, 1.0, 10)
        900.0
    """
    return round(total_gb * over_subscription_ratio * (1 - reserved_percentage / 100), 2)


def calculate_headroom(effective: float, used: float) -> float:
    """Calculate headroom (remaining capacity).

    Formula: effective - used

    Args:
        effective (float): Effective capacity after overcommit and reserves.
        used (float): Currently used capacity.

    Returns:
        float: Remaining capacity (headroom).

    Example:
        >>> calculate_headroom(2016, 54)
        1962
        >>> calculate_headroom(247360, 110592)
        136768
    """
    return effective - used


def calculate_utilization_pct(used: float, effective: float) -> float:
    """Calculate utilization as a percentage.

    Returns 0.0 when effective capacity is zero or negative to avoid
    division by zero.

    Args:
        used (float): Currently used capacity.
        effective (float): Effective capacity (denominator).

    Returns:
        float: Utilization percentage, rounded to 2 decimals.

    Example:
        >>> calculate_utilization_pct(54, 2016)
        2.68
        >>> calculate_utilization_pct(0, 2016)
        0.0
        >>> calculate_utilization_pct(100, 0)
        0.0
    """
    if effective <= 0:
        return 0.0
    return round((used / effective) * 100, 2)


def calculate_max_vms_for_host(vcpus_headroom: int,
                               ram_headroom_mb: int,
                               disk_headroom_gb: int,
                               flavor_vcpus: int,
                               flavor_ram_mb: int,
                               flavor_disk_gb: int) -> int:
    """Calculate the maximum number of VMs that can be hosted on a given host.

    Args:
        vcpus_headroom (int): Available vCPUs.
        ram_headroom_mb (int): Available RAM in MB.
        disk_headroom_gb (int): Available disk in GB.
        flavor_vcpus (int): vCPUs required by the VM flavor.
        flavor_ram_mb (int): RAM required by the VM flavor in MB.
        flavor_disk_gb (int): Disk required by the VM flavor in GB.

    Returns:
        int: Maximum number of VMs that can be hosted on the given host.

    Example:
        >>> calculate_max_vms_for_host(1962, 136768, 798, 4, 8192, 20)
        16
        >>> calculate_max_vms_for_host(0, 136768, 798, 4, 8192, 20)
        0
    """
    if vcpus_headroom <= 0 or ram_headroom_mb <= 0 or disk_headroom_gb <= 0:
        return 0

    limits = []
    if flavor_vcpus > 0:
        limits.append(vcpus_headroom // flavor_vcpus)
    if flavor_ram_mb > 0:
        limits.append(ram_headroom_mb // flavor_ram_mb)
    if flavor_disk_gb > 0:
        limits.append(disk_headroom_gb // flavor_disk_gb)

    if not limits:
        return 0

    return min(limits)


def determine_status(
    utilization_pct: float,
    warning_threshold_pct: float,
    critical_threshold_pct: float,
) -> str:
    """Determine capacity status based on utilization percentage.

    Args:
        utilization_pct (float): Current utilization percentage.
        warning_threshold_pct (float): Threshold for warning status.
        critical_threshold_pct (float): Threshold for critical status.

    Returns:
        str: Status string ('ok', 'warning', or 'critical').

    Example:
        >>> determine_status(50.0, 70.0, 90.0)
        'ok'
        >>> determine_status(75.0, 70.0, 90.0)
        'warning'
        >>> determine_status(95.0, 70.0, 90.0)
        'critical'
    """
    if utilization_pct >= critical_threshold_pct:
        return "critical"
    if utilization_pct >= warning_threshold_pct:
        return "warning"
    return "ok"

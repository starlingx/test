==========================================
OpenStack Capacity Keywords
==========================================

Keywords for collecting and analyzing OpenStack capacity data across
compute, storage, and network resources.

All keywords follow the ACE three-file pattern (Keyword → Output → Object)
and use ``source_admin_openrc`` for OpenStack CLI authentication.

Overview
========

The capacity keywords provide two layers:

1. **Data collection keywords** — execute individual OpenStack CLI commands
   and return parsed Output/Object instances.
2. **Capacity analysis keyword** — orchestrates the collection keywords,
   calculates effective capacity, headroom, utilization, and status for
   each hypervisor and storage pool.

Data Collection Keywords
========================

Compute
-------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Keyword
     - CLI Command
     - Description
   * - ``OpenStackHypervisorListKeywords``
     - ``openstack hypervisor list``
     - List hypervisors (ID, hostname, type, IP, state)
   * - ``OpenStackHypervisorStatsKeywords``
     - ``openstack hypervisor stats show``
     - Aggregate cluster stats (deprecated but functional)
   * - ``OpenStackResourceProviderListKeywords``
     - ``openstack resource provider list``
     - List resource provider UUIDs and names
   * - ``OpenStackResourceProviderInventoryListKeywords``
     - ``openstack resource provider inventory list <uuid>``
     - Per-hypervisor capacity (total, used, allocation_ratio, reserved)

Storage
-------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Keyword
     - CLI Command
     - Description
   * - ``CinderGetPoolsKeywords``
     - ``cinder get-pools --detail``
     - Storage pool capacity (total, free, allocated, oversubscription)
   * - ``OpenStackVolumeListKeywords``
     - ``openstack volume list --all-projects``
     - List all volumes (ID, name, status, size)
   * - ``OpenStackVolumeTypeListKeywords``
     - ``openstack volume type list``
     - List volume types

Network
-------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Keyword
     - CLI Command
     - Description
   * - ``OpenStackNetworkListKeywords``
     - ``openstack network list``
     - List networks (ID, name, subnets)
   * - ``OpenStackSubnetListKeywords``
     - ``openstack subnet list``
     - List subnets (ID, name, network, CIDR)
   * - ``OpenStackPortListKeywords``
     - ``openstack port list``
     - List ports with continuation line merging
   * - ``OpenStackFloatingIpListKeywords``
     - ``openstack floating ip list``
     - List floating IPs
   * - ``OpenStackFlavorListKeywords``
     - ``openstack flavor list --all``
     - List flavors (vCPUs, RAM, disk)

Capacity Analysis
=================

``OpenStackCapacityAnalysisKeywords`` orchestrates the collection keywords
and calculates derived metrics for every hypervisor and storage pool.

Formulas
--------

**Compute effective capacity** (per hypervisor, per resource)::

    effective = int(total * allocation_ratio) - reserved

**Storage effective capacity** (per Cinder pool)::

    effective = total_gb * max_over_subscription_ratio * (1 - reserved_percentage / 100)

**Headroom and utilization** (both compute and storage)::

    headroom = effective - used
    utilization_pct = (used / effective) * 100

**Status thresholds** (configurable, defaults shown)::

    utilization < 70%  → ok
    utilization >= 70% → warning
    utilization >= 90% → critical

**VM packing** (per hypervisor, then summed across cluster)::

    max_vms_on_host = min(
        vcpus_headroom   // flavor_vcpus,
        ram_headroom_mb  // flavor_ram_mb,
        disk_headroom_gb // flavor_disk_gb,
    )
    max_vms_cluster = sum(max_vms_on_host for each hypervisor)

The per-host calculation is more accurate than an aggregate calculation
because a VM must fit entirely on a single hypervisor.

Usage Examples
--------------

**Basic capacity analysis:**

.. code-block:: python

    from keywords.cloud_platform.openstack.capacity.openstack_capacity_analysis_keywords import (
        OpenStackCapacityAnalysisKeywords,
    )

    analysis_kw = OpenStackCapacityAnalysisKeywords(ssh_connection)
    output = analysis_kw.analyze_capacity()

    # Per-hypervisor breakdown
    for compute in output.get_compute_capacities():
        hostname = compute.get_hostname()
        vcpu_pct = compute.get_vcpus_utilization_pct()
        ram_pct = compute.get_memory_mb_utilization_pct()
        status = compute.get_status()  # 'ok', 'warning', or 'critical'

    # Aggregate headroom
    free_vcpus = output.get_aggregate_vcpus_headroom()
    free_ram = output.get_aggregate_memory_mb_headroom()
    free_disk = output.get_aggregate_disk_gb_headroom()

    # Storage pools
    for pool in output.get_storage_capacities():
        pool.get_headroom_gb()
        pool.get_utilization_pct()

**VM packing estimation:**

.. code-block:: python

    # How many m1.small VMs (1 vCPU, 2048 MB, 20 GB) fit in the cluster?
    max_vms = output.calculate_max_vms_for_flavor(1, 2048, 20)

    # Per-host breakdown
    per_host = output.calculate_max_vms_per_host(1, 2048, 20)
    # {'compute-0': 43, 'compute-1': 43, ...}

    # Loading table (VM count at each utilization level)
    table = output.calculate_loading_table(1, 2048, 20)
    # {10: 22, 20: 44, 30: 66, ..., 100: 221}

**Imbalance detection:**

.. code-block:: python

    ratio = output.get_imbalance_ratio()  # e.g. 42.5
    if output.is_imbalanced(threshold=30.0):
        # Cluster has significant imbalance between hypervisors
        most = output.get_most_utilized_compute()
        least = output.get_least_utilized_compute()

**JSON report:**

.. code-block:: python

    import json

    report = output.to_json()
    print(json.dumps(report, indent=2))

**Custom thresholds:**

.. code-block:: python

    output = analysis_kw.analyze_capacity(
        warning_threshold_pct=60.0,
        critical_threshold_pct=80.0,
    )

**Individual data collection keywords:**

.. code-block:: python

    from keywords.cloud_platform.openstack.hypervisor.openstack_hypervisor_list_keywords import (
        OpenStackHypervisorListKeywords,
    )
    from keywords.cloud_platform.openstack.resource_provider.openstack_resource_provider_inventory_list_keywords import (
        OpenStackResourceProviderInventoryListKeywords,
    )
    from keywords.cloud_platform.openstack.cinder.cinder_get_pools_keywords import (
        CinderGetPoolsKeywords,
    )

    # Hypervisor list
    hv_kw = OpenStackHypervisorListKeywords(ssh_connection)
    hv_output = hv_kw.get_openstack_hypervisor_list()
    for hv in hv_output.get_hypervisors():
        print(hv.get_hypervisor_hostname(), hv.get_state())

    # Resource provider inventory (per hypervisor)
    inv_kw = OpenStackResourceProviderInventoryListKeywords(ssh_connection)
    inv_output = inv_kw.get_resource_provider_inventory_list(hv.get_id())
    vcpu = inv_output.get_resource_provider_by_resource_class("VCPU")
    print(vcpu.get_total(), vcpu.get_used(), vcpu.get_allocation_ratio())

    # Cinder pools
    cinder_kw = CinderGetPoolsKeywords(ssh_connection)
    pools_output = cinder_kw.get_cinder_pools()
    for pool in pools_output.get_pools():
        print(pool.get_total_capacity_gb(), pool.get_free_capacity_gb())

Authentication
==============

All OpenStack keywords use ``source_admin_openrc`` from
``keywords.openstack.command_wrappers``. This sources
``/var/opt/openstack/admin-openrc`` and wraps commands with
``clients-wrapper.sh``, which is required for OpenStack service
endpoints (Nova, Cinder, Neutron).

Do **not** use ``source_openrc`` (platform commands only) for these
keywords — it will fail with endpoint-not-found errors.

Port List — Continuation Lines
==============================

``openstack port list`` produces continuation lines when a port has
multiple Fixed IP Addresses. The CLI output looks like::

    | abc-123 |      | fa:16:3e:aa:bb:cc | ip_address='10.0.0.1', subnet_id='sub-1' | ACTIVE |
    |         |      |                   | ip_address='10.0.0.2', subnet_id='sub-2' |        |

The ``OpenStackPortListOutput`` handles this by detecting rows with an
empty ID field and appending their Fixed IP Addresses to the previous
port object. The shared ``OpenStackTableParser`` is not modified.

File Structure
==============

::

    keywords/cloud_platform/openstack/
    ├── capacity/
    │   ├── capacity_math.py                              # Pure calculation helpers
    │   ├── openstack_capacity_analysis_keywords.py       # Orchestration keyword
    │   ├── README.rst                                    # This file
    │   └── object/
    │       ├── openstack_capacity_analysis_output.py     # Aggregated results
    │       ├── openstack_compute_capacity_object.py      # Per-hypervisor data
    │       └── openstack_storage_capacity_object.py      # Per-pool data
    ├── cinder/
    │   ├── cinder_get_pools_keywords.py
    │   └── object/
    ├── flavor/
    │   ├── openstack_flavor_list_keywords.py
    │   └── object/
    ├── floating_ip/
    │   ├── openstack_floating_ip_list_keywords.py
    │   └── object/
    ├── hypervisor/
    │   ├── openstack_hypervisor_list_keywords.py
    │   ├── openstack_hypervisor_stats_keywords.py
    │   └── object/
    ├── network/
    │   ├── openstack_network_list_keywords.py
    │   ├── openstack_subnet_list_keywords.py
    │   └── object/
    ├── port/
    │   ├── openstack_port_list_keywords.py
    │   └── object/
    ├── resource_provider/
    │   ├── openstack_resource_provider_inventory_list_keywords.py
    │   ├── openstack_resource_provider_list_keywords.py
    │   └── object/
    └── volume/
        ├── openstack_volume_list_keywords.py
        ├── openstack_volume_type_list_keywords.py
        └── object/

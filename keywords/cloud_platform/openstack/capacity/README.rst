==========================================
OpenStack Capacity Keywords
==========================================

Keywords for collecting and analyzing OpenStack capacity data across
compute, storage, and network resources.

All capacity-related keywords use the **OpenStack SDK** (``openstacksdk``)
via ``ACEOpenStackConnection`` for direct API access with automatic
logging. This replaces the previous CLI-over-SSH approach for improved
performance and reliability.

Overview
========

The capacity keywords provide two layers:

1. **Data collection keywords** — use the OpenStack SDK to query Placement
   and Block Storage APIs, returning parsed Output/Object instances.
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
     - SDK API
     - Description
   * - ``OpenStackResourceProviderListKeywords``
     - ``placement.resource_providers()``
     - List resource provider UUIDs and names
   * - ``OpenStackResourceProviderInventoryListKeywords``
     - ``GET /resource_providers/{uuid}/inventories`` + ``/usages``
     - Per-hypervisor capacity (total, used, allocation_ratio, reserved)

Storage
-------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Keyword
     - SDK API
     - Description
   * - ``CinderGetPoolsKeywords``
     - ``block_storage.backend_pools(details=True)``
     - Storage pool capacity (total, free, allocated, oversubscription)

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

    from keywords.openstack.connection.openstack_connection_manager import create_ace_connection
    from keywords.cloud_platform.openstack.capacity.openstack_capacity_analysis_keywords import (
        OpenStackCapacityAnalysisKeywords,
    )

    conn = create_ace_connection(ssh_connection)

    analysis_kw = OpenStackCapacityAnalysisKeywords(conn)
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

    from keywords.openstack.connection.openstack_connection_manager import create_ace_connection
    from keywords.cloud_platform.openstack.resource_provider.openstack_resource_provider_list_keywords import (
        OpenStackResourceProviderListKeywords,
    )
    from keywords.cloud_platform.openstack.resource_provider.openstack_resource_provider_inventory_list_keywords import (
        OpenStackResourceProviderInventoryListKeywords,
    )
    from keywords.cloud_platform.openstack.cinder.cinder_get_pools_keywords import (
        CinderGetPoolsKeywords,
    )

    conn = create_ace_connection(ssh_connection)

    # Resource provider list
    rp_kw = OpenStackResourceProviderListKeywords(conn)
    rp_output = rp_kw.get_resource_provider_list()
    for rp in rp_output.get_resource_providers():
        print(rp.get_name(), rp.get_uuid())

    # Resource provider inventory (per hypervisor)
    inv_kw = OpenStackResourceProviderInventoryListKeywords(conn)
    inv_output = inv_kw.get_resource_provider_inventory_list(rp.get_uuid())
    vcpu = inv_output.get_resource_provider_by_resource_class("VCPU")
    print(vcpu.get_total(), vcpu.get_used(), vcpu.get_allocation_ratio())

    # Cinder pools
    cinder_kw = CinderGetPoolsKeywords(conn)
    pools_output = cinder_kw.get_cinder_pools()
    for pool in pools_output.get_pools():
        print(pool.get_total_capacity_gb(), pool.get_free_capacity_gb())

Authentication
==============

All capacity keywords accept an ``ACEOpenStackConnection`` instance.
Use the ``create_ace_connection()`` factory which extracts credentials
from the lab via SSH and creates an authenticated SDK connection with
automatic logging of all service calls.

.. code-block:: python

    from keywords.openstack.connection.openstack_connection_manager import create_ace_connection
    from keywords.cloud_platform.ssh.lab_connection_keywords import LabConnectionKeywords

    ssh = LabConnectionKeywords().get_active_controller_ssh()
    conn = create_ace_connection(ssh)

**Required service endpoints:**

- **Placement** — for resource provider and inventory queries
- **Block Storage (Cinder)** — for storage pool capacity

File Structure
==============

::

    keywords/cloud_platform/openstack/
    ├── capacity/
    │   ├── capacity_math.py                              # Pure calculation helpers
    │   ├── openstack_capacity_analysis_keywords.py       # Orchestration keyword (SDK)
    │   ├── README.rst                                    # This file
    │   └── object/
    │       ├── openstack_capacity_analysis_output.py     # Aggregated results
    │       ├── openstack_compute_capacity_object.py      # Per-hypervisor data
    │       └── openstack_storage_capacity_object.py      # Per-pool data
    ├── cinder/
    │   ├── cinder_get_pools_keywords.py                  # SDK: block_storage.backend_pools()
    │   └── object/
    │       ├── cinder_get_pools_object.py
    │       └── cinder_get_pools_output.py
    └── resource_provider/
        ├── openstack_resource_provider_list_keywords.py             # SDK: placement.resource_providers()
        ├── openstack_resource_provider_inventory_list_keywords.py   # SDK: placement GET inventories/usages
        └── object/
            ├── openstack_resource_provider_list_object.py
            ├── openstack_resource_provider_list_output.py
            ├── openstack_resource_provider_inventory_list_object.py
            └── openstack_resource_provider_inventory_list_output.py

Migration from CLI
==================

The keyword files previously used SSH + CLI commands (e.g.
``openstack resource provider list``, ``cinder get-pools --detail``).
They now use the OpenStack SDK via ``ACEOpenStackConnection``.

**What changed:**

- Keyword constructors accept ``ACEOpenStackConnection`` instead of ``SSHConnection``
- No more SSH, CLI parsing, or table parser dependency
- Output classes accept SDK response objects directly in their constructors
- Extends ``BaseKeyword`` for keyword-level logging and future failure grouping

**What stayed the same:**

- All Object classes (data holders) are unchanged
- The ``capacity_math.py`` helper functions are unchanged
- The ``OpenStackCapacityAnalysisOutput`` aggregation class is unchanged
- All public method signatures on Output/Object classes are unchanged

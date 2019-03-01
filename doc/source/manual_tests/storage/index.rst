==================
Storage Regression
==================


This test plan covers Storage regression.  It covers basic functionality for
the following features:

- HPE3PAR
- EMC SAN
- Storage Tiering
- Ceph Replication Factor 3
- Swift
- Ceph OSD and Ceph Monitor Process Kills
- Storage Node Scalability
- Core Tests (Lock semantic tests, host reinstall, host delete and
  re-provision)
- Journaling of disks
- Hardware disk replacements
- Host partition basic tests
- Dead-office-recovery test (DOR)
- Ceph storage pool and filesystem modifications
- Nova actions on various VMs (including boot from volume with volume
  attachments)

--------------------
Overall Requirements
--------------------

This test will require access to the following configurations:

- EMC SAN
- Extra disks (SSDs and NVMe drives)
- Systems with 8 storage nodes
- HPE3PAR
- All-in-One Simplex systems
- All-in-One Duplex systems
- Standard systems

----------
Test Cases
----------

.. contents::
   :local:
   :depth: 1

~~~~~~~~~~~~~
STOR_3PAR_001
~~~~~~~~~~~~~

:Test ID: STOR_3PAR_001
:Test Title: test_basic_hpe3par_feature_enable
:Tags: p1, storage, ceph, hpe3par, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that HPE3PAR can be successfully
enabled in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

HPE3PAR present and configured properly

++++++++++
Test Steps
++++++++++

1. View the system service parameters via:

   .. code:: bash

      system service-parameter-list

2. Enable HPE3PAR for a backend using the following commands:

   .. code:: bash

      system service-parameter-modify cinder hpe3par enabled=true
      system service-parameter-add cinder hpe3par hpe3par_api_url=https://<ip:port>/api/v1
      system service-parameter-add cinder hpe3par hpe3par_username=<username>
      system service-parameter-add cinder hpe3par hpe3par_password=<password>
      system service-parameter-add cinder hpe3par hpe3par_iscsi_ips=<ip1,ip2,ip3>
      system service-parameter-add cinder hpe3par hpe3par_cpg=<cpg_name>
      system service-parameter-add cinder hpe3par hpe3par_cpg_snap=<cpg_name
      system service-parameter-add cinder hpe3par hpe3par_snapshot_expiration=72
      system service-parameter-add cinder hpe3par hpe3par_iscsi_chap_enabled=true
      system service-parameter-add cinder hpe3par san_ip=<san_ip>
      system service-parameter-add cinder hpe3par san_login=<username>
      system service-parameter-add cinder hpe3par san_password=<password>
      system service-parameter-add cinder hpe3par hpe3par_debug=false

3. Repeat step 2 for backends: hpe3par, hpe3par2 to hpe3par12.
4. Apply the parameters:

   .. code:: bash

      system service-parameter-apply cinder

5. Check the hpe3par configuration in cinder.conf.  You should see
   *hpe3par* referenced in the conf file.  Ensure the information is correct.
6. Create a cinder volume type to use the HPE3PAR backend:

   .. code:: bash

      cinder type-create 3par-backend
      cinder type-key 3par-backend set hpe3par:provisioning=dedup volume_backend_name=hpe3par
      cinder type-show 3par-backend
      cinder extra-specs-list

7. Repeat step 6 for all backends.
8. Create a volume using one of the HPE3PAR backends.
9. Ensure the volume is created in the correct CPG by checking the HPE3PAR
   server.
10. Ensure you can launch a VM from the newly created HPE3PAR volume.
11. Do some basic tests such as migrations and nova operations to ensure the
    system is working properly.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

HPE3PAR is successfully enabled and HPE3PAR volumes can be launched


~~~~~~~~~~~~~
STOR_3PAR_002
~~~~~~~~~~~~~

:Test ID: STOR_3PAR_002
:Test Title: test_basic_hpe3par_feature_disable
:Tags: p1, storage, ceph, hpe3par, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that HPE3PAR can be successfully
disabled in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- HPE3PAR present and configured properly.
- HPE3PAR volume(s) present

++++++++++
Test Steps
++++++++++

1.  Attempt to disable HPE3PAR while HPE3PAR volumes are present:

    .. code:: bash

       system service-parameter-modify cinder hpe3par enabled=false
       system service-parameter-apply cinder

2.  Ensure this is rejected due to HPE3PAR volumes being present
3.  Delete the HPE3PAR volumes
4.  Ensure you can now disable HPE3PAR

+++++++++++++++++
Expected Behavior
+++++++++++++++++
HPE3PAR can be successfully disabled once it is no longer in use.


~~~~~~~~~~~~
STOR_SAN_003
~~~~~~~~~~~~

:Test ID: STOR_SAN_003
:Test Title: test_basic_emcsan_feature_enable
:Tags: p1, storage, ceph, emcsan, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that EMC SAN can be successfully
enabled in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- EMC SAN present and configured properly.

++++++++++
Test Steps
++++++++++

1.  View the system service parameters via:

    .. code:: bash

       system service-parameter-list

2.  Enable EMC SAN using the following parameters:

    .. code:: bash

       system service-parameter-modify cinder emc_vnx enabled=true
       system service-parameter-add cinder emc_vnx control_network=oam
       system service-parameter-add cinder emc_vnx data_network=<mgmt|infra>
       system service-parameter-add cinder emc_vnx storage_vnx_pool_names=<poolname>
       system service-parameter-add cinder emc_vnx san_ip=<san_ip>
       system service-parameter-add cinder emc_vnx san_login=<username>
       system service-parameter-add cinder emc_vnx san_password=<password>
       system service-parameter-add cinder san_secondary_ip=<ip>
       system service-parameter-add cinder default_timeout=<timeout>
       system service-parameter-add cinder emc_vnx io_port_list=ioPortList

3.  Apply the changes via:

    .. code:: bash

       system service-parameter-apply cinder

    Note: the system will go config out-of-date and then clear
4.  Create EMC SAN cinder types via the following commands:

    .. code:: bash

       cinder type-create emc-thick
       cinder type-key emc-think set provisioning:type=thick volume_backend_name=emc_vnx
       cinder type-create emc-thin
       cinder type-key emc-think set provisioning:type=thin volume_backend_name=emc_vnx
       cinder type-create emc-compressed
       cinder type-key emc-compressed set provisioning:type=compressed volume_backend_name=emc_vnx
       cinder type-create emc-thin-on-auto-tier
       cinder type-key emc-think-tier-auto set provisioning:type=thin storagetype:tiering=Auto volume_backend_name=emc_vnx

5.  Create a volume using one of the cinder types:

    .. code:: bash

       cinder create --volume_type emc-thin --display_name vol1 1

6.  Using the newly created volume, boot a VM.
7.  Do some migrations and perform some nova actions to ensure the system
    is working properly.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

EMC SAN can be successfully enabled and EMC SAN volumes can be launched


~~~~~~~~~~~~
STOR_SAN_004
~~~~~~~~~~~~

:Test ID: STOR_SAN_004
:Test Title: test_basic_emcsan_feature_disable
:Tags: p1, storage, ceph, emcsan, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that EMC SAN can be successfully
disabled in StarlingX.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- EMC SAN present and configured properly.

++++++++++
Test Steps
++++++++++

1.  Attempt to disable EMC SAN while EMC SAN volumes are present:

    .. code:: bash

       system service-parameter-modify cinder emc_vnx enabled=false
       system service-parameter-apply cinder

2.  Ensure this is rejected due to EMC SAN volumes being present
3.  Delete the EMC SAN volumes
4.  Ensure you can now disable EMC SAN

+++++++++++++++++
Expected Behavior
+++++++++++++++++

EMC SAN can be successfully disabled once it is no longer in use.


~~~~~~~~~~~~~
STOR_TIER_005
~~~~~~~~~~~~~

:Test ID: STOR_TIER_005
:Test Title: test_create_new_storage_tier
:Tags: p1, storage, ceph, tier, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that a new storage tier can be
created.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System contains storage nodes
- Storage nodes contain unassigned disks

++++++++++
Test Steps
++++++++++

1.  Use system cluster-list to show the existing storage cluster(s), e.g.:

    .. code:: bash

       [wrsroot@controller-1 ~(keystone_admin)]$ system cluster-list
       +--------------------------------------+--------------------------------------+------+--------------+
       | uuid                                 | cluster_uuid                         | type | name         |
       +--------------------------------------+--------------------------------------+------+--------------+
       | d3af37b5-862e-4faa-ad2a-c65fb937a92f | fbf36662-d5c2-4e25-969d-cd6fac0758b4 | ceph | ceph_cluster |
       +--------------------------------------+--------------------------------------+------+--------------+

    Ensure the information is accurate.
2.  Use storage-tier-list to show the existing storage tier(s), e.g.:

    .. code:: bash

       [wrsroot@controller-1 ~(keystone_admin)]$ system storage-tier-list d3af37b5-862e-4faa-ad2a-c65fb937a92f
       +--------------------------------------+---------+--------+--------------------------------------+
       | uuid                                 | name    | status | backend_using                        |
       +--------------------------------------+---------+--------+--------------------------------------+
       | 2afeebb6-6587-401b-8f56-f50aed62a45a | storage | in-use | 29c52149-f8a3-4e13-8644-c0c5b876ba62 |
       +--------------------------------------+---------+--------+--------------------------------------+

    Ensure the information is accurate.
3.  Add a new storage tier via:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-tier-add ceph_cluster gold
       +--------------+--------------------------------------+
       | Property     | Value                                |
       +--------------+--------------------------------------+
       | uuid         | 78895dc0-16c0-4ec3-895e-ca28bfaa378c |
       | name         | gold                                 |
       | type         | ceph                                 |
       | status       | defined                              |
       | backend_uuid | None                                 |
       | cluster_uuid | 498d4063-e526-4c08-8d19-81df7a094e75 |
       | OSDs         | []                                   |
       | created_at   | 2018-02-15T15:56:33.610855+00:00     |
       | updated_at   | None                                 |
       +--------------+--------------------------------------+

    Ensure the information is accurate.
4.  Confirm the tier has been added, e.g.:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-tier-list 498d4063-e526-4c08-8d19-81df7a094e75
       +--------------------------------------+---------+---------+--------------------------------------+
       | uuid                                 | name    | status  | backend_using                        |
       +--------------------------------------+---------+---------+--------------------------------------+
       | 78895dc0-16c0-4ec3-895e-ca28bfaa378c | gold    | defined | None                                 |
       | b702a76b-f189-44e5-9cd1-6847fbad5d88 | storage | in-use  | 7d0fa3e1-5b16-497d-9c2c-b2e74bf58c68 |
       +--------------------------------------+---------+---------+--------------------------------------+

Ensure the information is accurate.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Additional storage tier is successfully created.


~~~~~~~~~~~~~
STOR_TIER_006
~~~~~~~~~~~~~

:Test ID: STOR_TIER_006
:Test Title: test_associate_storage_tier_with_osd
:Tags: p1, storage, ceph, tier, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that a new storage tier can be
associated with an OSD.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System contains storage nodes
- Storage tier has been created
- Storage nodes contain unassigned disks

++++++++++
Test Steps
++++++++++

1.  Associate some unused OSDs with the tier using the CLI (note storage
host needs to be locked for this).  Use this to see which OSDs are already
assigned:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system host-stor-list storage-0
       +--------------------------------------+----------+-------+--------------+--------------------------------------+-----------------------------------------------------------------------+--------------+------------------+-----------+
       | uuid                                 | function | osdid | capabilities | idisk_uuid                           | journal_path                                                          | journal_node | journal_size_mib | tier_name |
       +--------------------------------------+----------+-------+--------------+--------------------------------------+-----------------------------------------------------------------------+--------------+------------------+-----------+
       | 897e2eb2-3cc3-49a9-8ba9-9fc825b33e90 | osd      | 2     | {}           | 92f6bf46-bfc0-43b0-ade5-706f119e7696 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3d93ad-lun-0-part2 | /dev/sde2    | 1024             | storage   |
       | 8c0ad536-8d2b-4e25-95a3-a1cce28d0c7c | osd      | 3     | {}           | 2dfc0f81-4b09-4c22-a066-582140d817d0 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3f97ad-lun-0-part2 | /dev/sdf2    | 1024             | storage   |
       | 987da99e-a931-4167-9894-700350349773 | osd      | 0     | {}           | bcafc152-c49e-4216-b41a-043dd195a3a7 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3fa1fd-lun-0-part2 | /dev/sdc2    | 1024             | storage   |
       | b8764a42-dd13-421d-83b9-c2be9b58c829 | osd      | 1     | {}           | d47aba68-bd3c-4265-a57f-184051007742 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3fa189-lun-0-part2 | /dev/sdd2    | 1024             | storage   |
       | c3919818-3dc6-45b0-87bf-0f0d2e1505c9 | osd      | 4     | {}           | 53855d3a-4af4-4e7a-92e5-2a3b2bc106b9 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c4033fd-lun-0-part2 | /dev/sdg2    | 1024             | storage   |
       +--------------------------------------+----------+-------+--------------+--------------------------------------+-----------------------------------------------------------------------+--------------+------------------+-----------+

2.  Use this to see what disks are available:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system host-disk-list storage-0
       +--------------------------------------+-------------+------------+-------------+----------+---------------+--------------+----------------------+-----------------------------------------------------------------+
       | uuid                                 | device_node | device_num | device_type | size_mib | available_mib | rpm          | serial_id            | device_path                                                     |
       +--------------------------------------+-------------+------------+-------------+----------+---------------+--------------+----------------------+-----------------------------------------------------------------+
       | 94fbf5f8-c64c-4966-bd4c-ab3138e0d3c1 | /dev/sda    | 2048       | SSD         | 228936   | 223814        | N/A          | BTWL330608M8240NGN   | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5001e67680f0d000-lun-0 |
       | 1ae6a2a9-281f-4f0a-899a-e704b69a0fb2 | /dev/sdb    | 2064       | HDD         | 858483   | 0             | Undetermined | S0N196T50000M4336QDY | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c50071d9540d-lun-0 |
       | bcafc152-c49e-4216-b41a-043dd195a3a7 | /dev/sdc    | 2080       | HDD         | 286102   | 0             | Undetermined | 6XN55RWV0000B417C3CM | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3fa1fd-lun-0 |
       | d47aba68-bd3c-4265-a57f-184051007742 | /dev/sdd    | 2096       | HDD         | 286102   | 0             | Undetermined | 6XN56CNT0000B4179NY0 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3fa189-lun-0 |
       | 92f6bf46-bfc0-43b0-ade5-706f119e7696 | /dev/sde    | 2112       | HDD         | 286102   | 0             | Undetermined | 6XN562V20000B416G7X1 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3d93ad-lun-0 |
       | 2dfc0f81-4b09-4c22-a066-582140d817d0 | /dev/sdf    | 2128       | HDD         | 286102   | 0             | Undetermined | 6XN53FXN0000B416K6WN | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3f97ad-lun-0 |
       | 53855d3a-4af4-4e7a-92e5-2a3b2bc106b9 | /dev/sdg    | 2144       | HDD         | 286102   | 0             | Undetermined | 6XN56AK80000B417C4GA | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c4033fd-lun-0 |
       +--------------------------------------+-------------+------------+-------------+----------+---------------+--------------+----------------------+-----------------------------------------------------------------+

3.  To see the naming for the backends:

    .. code:: bash

       [wrsroot@controller-1 ~(keystone_admin)]$ system storage-backend-list
       +--------------------------------------+------------+---------+------------+------+----------+---------------------------+
       | uuid                                 | name       | backend | state      | task | services | capabilities              |
       +--------------------------------------+------------+---------+------------+------+----------+---------------------------+
       | 29c52149-f8a3-4e13-8644-c0c5b876ba62 | ceph-store | ceph    | configured | None | cinder,  | {u'min_replication': u'2',|
       |                                      |            |         |            |      | glance   |  u'replication': u'3'}    |
       | df9186cf-4943-4c65-83b2-0fc47084a481 | file-store | file    | configured | None | glance   | {}                        |
       +--------------------------------------+------------+---------+------------+------+----------+---------------------------+

4.  To associate OSDs (where tier-uuid is the uuid of the new storage tier
    taken from system storage-tier-list)

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system host-stor-add storage-0 94fbf5f8-c64c-4966-bd4c-ab3138e0d3c1 --tier-uuid 78895dc0-16c0-4ec3-895e-ca28bfaa378c
       +------------------+-----------------------------------------------------------------------+
       | Property         | Value                                                                 |
       +------------------+-----------------------------------------------------------------------+
       | osdid            | 10                                                                    |
       | function         | osd                                                                   |
       | journal_location | 125363b8-ab6e-4d0b-a237-e9049f386e0a                                  |
       | journal_size_mib | 1024                                                                  |
       | journal_path     | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5001e67680f0d000-lun-0-part2 |
       | journal_node     | /dev/sda2                                                             |
       | uuid             | 125363b8-ab6e-4d0b-a237-e9049f386e0a                                  |
       | ihost_uuid       | ab2dd045-16b3-4d8e-83cd-6757743e9474                                  |
       | idisk_uuid       | 94fbf5f8-c64c-4966-bd4c-ab3138e0d3c1                                  |
       | tier_uuid        | 78895dc0-16c0-4ec3-895e-ca28bfaa378c                                  |
       | tier_name        | gold                                                                  |
       | created_at       | 2018-02-15T16:04:50.395659+00:00                                      |
       | updated_at       | 2018-02-15T16:05:06.672584+00:00                                      |
       +------------------+-----------------------------------------------------------------------+

5.  Check that the storage tier goes from 'defined' to 'in-use':

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-tier-list ceph_cluster
       +--------------------------------------+---------+--------+--------------------------------------+
       | uuid                                 | name    | status | backend_using                        |
       +--------------------------------------+---------+--------+--------------------------------------+
       | 8e35cc1a-a3e0-415a-a4c0-db31e03aeda8 | gold    | in-use | None                                 |
       | b702a76b-f189-44e5-9cd1-6847fbad5d88 | storage | in-use | 7d0fa3e1-5b16-497d-9c2c-b2e74bf58c68 |
       +--------------------------------------+---------+--------+--------------------------------------+

6.  Check that the OSD is now assigned to the newly created tier:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system host-stor-list storage-0
       +--------------------------------------+----------+-------+--------------+--------------------------------------+-----------------------------------------------------------------------+--------------+------------------+-----------+
       | uuid                                 | function | osdid | capabilities | idisk_uuid                           | journal_path                                                          | journal_node | journal_size_mib | tier_name |
       +--------------------------------------+----------+-------+--------------+--------------------------------------+-----------------------------------------------------------------------+--------------+------------------+-----------+
       | 125363b8-ab6e-4d0b-a237-e9049f386e0a | osd      | 10    | {}           | 94fbf5f8-c64c-4966-bd4c-ab3138e0d3c1 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5001e67680f0d000-lun-0-part2 | /dev/sda2    | 1024             | gold      |
       | 897e2eb2-3cc3-49a9-8ba9-9fc825b33e90 | osd      | 2     | {}           | 92f6bf46-bfc0-43b0-ade5-706f119e7696 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3d93ad-lun-0-part2 | /dev/sde2    | 1024             | storage   |
       | 8c0ad536-8d2b-4e25-95a3-a1cce28d0c7c | osd      | 3     | {}           | 2dfc0f81-4b09-4c22-a066-582140d817d0 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3f97ad-lun-0-part2 | /dev/sdf2    | 1024             | storage   |
       | 987da99e-a931-4167-9894-700350349773 | osd      | 0     | {}           | bcafc152-c49e-4216-b41a-043dd195a3a7 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3fa1fd-lun-0-part2 | /dev/sdc2    | 1024             | storage   |
       | b8764a42-dd13-421d-83b9-c2be9b58c829 | osd      | 1     | {}           | d47aba68-bd3c-4265-a57f-184051007742 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c3fa189-lun-0-part2 | /dev/sdd2    | 1024             | storage   |
       | c3919818-3dc6-45b0-87bf-0f0d2e1505c9 | osd      | 4     | {}           | 53855d3a-4af4-4e7a-92e5-2a3b2bc106b9 | /dev/disk/by-path/pci-0000:04:00.0-sas-0x5000c5006c4033fd-lun-0-part2 | /dev/sdg2    | 1024             | storage   |
       +--------------------------------------+----------+-------+--------------+--------------------------------------+-----------------------------------------------------------------------+--------------+------------------+-----------+

7.  Unlock storage host
8.  Repeat assignment procedure on other storage host (but this time use
    Horizon)
9.  Check the disk assignments in ceph:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ ceph osd tree
       ID WEIGHT  TYPE    NAME       UP/DOWN REWEIGHT PRIMARY-AFFINITY
       -6 0.43439 root    gold-tier
       -7 0.43439 chassis group-0-gold
       -8 0.21719 host    storage-0-gold
       10 0.21719         osd.10     up      1.00000  1.00000
       -9 0.21719 host    storage-1-gold
       11 0.21719         osd.11     up      1.00000  1.00000
       -2 0 root  cache-tier
       -1 2.71698 root    storage-tier
       -3 2.71698 chassis group-0
       -4 1.35849 host    storage-0
       0 0.27170          osd.0     up      1.00000  1.00000
       1 0.27170          osd.1     up      1.00000  1.00000
       2 0.27170          osd.2     up      1.00000  1.00000
       3 0.27170          osd.3     up      1.00000  1.00000
       4 0.27170          osd.4     up      1.00000  1.00000
       -5 1.35849 host    storage-1
       5 0.27170          osd.5     up      1.00000  1.00000
       6 0.27170          osd.6     up      1.00000  1.00000
       7 0.27170          osd.7     up      1.00000  1.00000
       8 0.27170          osd.8     up      1.00000  1.00000
       9 0.27170          osd.9     up      1.00000  1.00000

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Storage tier is successfully associated with OSD


~~~~~~~~~~~~~
STOR_TIER_007
~~~~~~~~~~~~~

:Test ID: STOR_TIER_007
:Test Title: test_associate_storage_tier_with_backend
:Tags: p1, storage, ceph, tier, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that a new storage tier can be
associated with a backend.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System contains storage nodes
- Storage tier has been created and associated with an OSD

++++++++++
Test Steps
++++++++++

1.  Assuming a storage tier has already been created, and OSDs assigned,
    attempt to associate a storage tier with a backend:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-tier-list ceph_cluster
       +--------------------------------------+---------+--------+--------------------------------------+
       | uuid                                 | name    | status | backend_using                        |
       +--------------------------------------+---------+--------+--------------------------------------+
       | 8e35cc1a-a3e0-415a-a4c0-db31e03aeda8 | gold    | in-use | None                                 |
       | b702a76b-f189-44e5-9cd1-6847fbad5d88 | storage | in-use | 7d0fa3e1-5b16-497d-9c2c-b2e74bf58c68 |
       +--------------------------------------+---------+--------+--------------------------------------+

2. Associate a storage tier with a backend

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-backend-add --name gold-store -t 8e35cc1a-a3e0-415a-a4c0-db31e03aeda8 ceph
       System configuration has changed. Please follow the administrator guide to
       complete configuring the system.
       +--------------------------------------+------------+---------+------------+------+----------+-----------------------+
       | uuid                                 | name       | backend | state      | task | services | capabilities          |
       +--------------------------------------+------------+---------+------------+------+----------+-----------------------+
       | 3d7c03fd-8b1d-47ce-b1fb-0db3d8082e33 | file-store | file    | configured | None | glance   | {}                    |
       | 7d0fa3e1-5b16-497d-9c2c-b2e74bf58c68 | ceph-store | ceph    | configured | None | cinder,  | {u'min_replication':  |
       |                                      |            |         |            |      | glance   |  u'1', u'replication':|
       |                                      |            |         |            |      |          |  u'2'}                |
       | a61a629e-454b-4cb2-a6ba-20e5fde277e8 | gold-store | ceph    | configured | None | None     | {u'min_replication':  |
       |                                      |            |         |            |      |          |  u'1', u'replication':|
       |                                      |            |         |            |      |          |  u'2'}                |
       |                                      |            |         |            |      |          |                       |
       +--------------------------------------+------------+---------+------------+------+----------+-----------------------

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Storage tier can be successfully associated with a backend


~~~~~~~~~~~~~
STOR_TIER_008
~~~~~~~~~~~~~

:Test ID: STOR_TIER_008
:Test Title: test_associate_services_with_new_storage_tier
:Tags: p1, storage, ceph, tier, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure you can associate services with a
new storage tier.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System contains storage nodes
- Storage tier has been created, associated with an OSD and a backend

++++++++++
Test Steps
++++++++++

1.  Enable cinder on the new storage tier:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-backend-modify -s cinder gold-store
       +----------------------+--------------------------------------------------------------------------------+
       | Property             | Value                                                                          |
       +----------------------+--------------------------------------------------------------------------------+
       | backend              | ceph                                                                           |
       | name                 | gold-store                                                                     |
       | state                | configuring                                                                    |
       | task                 | {u'controller-1': 'applying-manifests', u'controller-0': 'applying-manifests'} |
       | services             | cinder                                                                         |
       | capabilities         | {u'min_replication': u'1', u'replication': u'2'}                               |
       | object_gateway       | False                                                                          |
       | ceph_total_space_gib | 222                                                                            |
       | object_pool_gib      | None                                                                           |
       | cinder_pool_gib      | 10                                                                             |
       | glance_pool_gib      | 10                                                                             |
       | ephemeral_pool_gib   | 10                                                                             |
       | tier_name            | gold                                                                           |
       | tier_uuid            | 8e35cc1a-a3e0-415a-a4c0-db31e03aeda8                                           |
       | created_at           | 2018-02-15T18:16:50.112399+00:00                                               |
       | updated_at           | 2018-02-15T18:51:42.639102+00:00                                               |
       +----------------------+--------------------------------------------------------------------------------+

    This should be successful.
2.  Confirm that the correct services are listed for the new tier:

    .. code:: bash

       [wrsroot@controller-0 ~(keystone_admin)]$ system storage-backend-list
       +--------------------------------------+------------+---------+------------+------+----------+-----------------------+
       | uuid                                 | name       | backend | state      | task | services | capabilities          |
       +--------------------------------------+------------+---------+------------+------+----------+-----------------------+
       | 3d7c03fd-8b1d-47ce-b1fb-0db3d8082e33 | file-store | file    | configured | None | glance   | {}                    |
       | 7d0fa3e1-5b16-497d-9c2c-b2e74bf58c68 | ceph-store | ceph    | configured | None | cinder,  | {u'min_replication':  |
       |                                      |            |         |            |      | glance   |  u'1', u'replication':|
       |                                      |            |         |            |      |          |  u'2'}                |
       |                                      |            |         |            |      |          |                       |
       | a61a629e-454b-4cb2-a6ba-20e5fde277e8 | gold-store | ceph    | configured | None | cinder   | {u'min_replication':  |
       |                                      |            |         |            |      |          |  u'1', u'replication':|
       |                                      |            |         |            |      |          |  u'2'}                |
       |                                      |            |         |            |      |          |                       |
       +--------------------------------------+------------+---------+------------+------+----------+-----------------------+

3.  Ensure you can create a new volume in the new storage tier
4.  Launch a VM from that volume and perform some migrations to ensure the
    system is working properly.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The new storage tier can be used.


~~~~~~~~~~~~~
STOR_REPF_009
~~~~~~~~~~~~~

:Test ID: STOR_REPF_009
:Test Title: test_basic_system_provisioning
:Tags: p1, storage, ceph, replication_factor3, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure you can provision the system to
have replication factor 3.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System contains storage nodes

++++++++++
Test Steps
++++++++++

1.  During an install of system, try some invalid values for the command:

    .. code::bash

       system storage-backend-add ceph -s cinder, glance replication=<numeric_value> min_replication=<numeric_value>

    - Try alphabetic characters
    - Try symbols
    - Try spaces
    - Try setting replication to a numeric value other than 2 or 3
    - Try setting min_replication to a numeric value other than 2
    - Try omitting the min_replication field (this should default to 2, assuming
      replication is present and set to 3)
2.  Use valid values for replication and min_replication. Replication
    should be set to 3 and min_replication to 2.
3.  Confirm the parameters are being applied via:

    .. code::bash

       system storage-backend-list

4.  Confirm that a config out-of-date alarm is raised and cleared on the
controllers while the manifests are applied
5.  Confirm ceph health is okay after provisioning is complete
6.  Confirm the 'ceph osd pool data size and min_size' values
7.  Ensure there are 3 storage nodes in each group using:

    .. code:: bash

       system cluster-list

8.  Confirm the crush map is set to replication factor 3
9.  Create some images and some instances (boot from volume with ephemeral
    and swap)
10.  Confirm using rbd that the data is stored in 3 locations
11.  Attempt to lower the replication factor from 3 to 2
12.  Ensure this is rejected

+++++++++++++++++
Expected Behavior
+++++++++++++++++

After replication factor 3 is enabled, there are 3 copies of the data
present on the system.


~~~~~~~~~~~~~~
STOR_SWIFT_010
~~~~~~~~~~~~~~

:Test ID: STOR_SWIFT_010
:Test Title: test_basic_swift_provisioning
:Tags: p1, storage, ceph, swift, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure you can use swift on the
system.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System must have ceph-enabled

++++++++++
Test Steps
++++++++++

1.  Run

    .. code:: bash

       system storage-backend-show ceph

    and ensure that swift is enabled as a service
2.  Run:

    .. code:: bash

       ceph df

    and ensure the swift object pools are listed
3.  The object service should be listed via

    .. code:: bash

       sudo sm-dump

    on the active controller (ceph-radosgw)
4. Create a container and create some objects using the Object Storage
   panel in Horizon to ensure swift is working properly.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Swift should be successfully enabled at the end of this test.


~~~~~~~~~~~~~~~~
STOR_PROCESS_011
~~~~~~~~~~~~~~~~

:Test ID: STOR_PROCESS_011
:Test Title: test_ceph_monitor_process_kill
:Tags: p1, storage, ceph, mtc, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to repeatedly kill the ceph monitor process
and ensure they are restarted by the system.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System must have ceph-enabled

++++++++++
Test Steps
++++++++++

1.  Check the health of cluster by typing

    .. code:: bash

       ceph -s

    The cluster health should report ok. the monitors should also be
    listed.  typically they will be controller-0, controller1 and storage-0.
2.  ssh to one of the controllers and get the pid of the monitor via

    .. code:: bash

       ps -ef | grep ceph

3.  Kill the monitor process and verify the process is terminated. Also
    validate

    .. code:: bash

       ceph -s

    updates the monitors appropriately.
4.  Verify the process is restarted by the system within the monitoring
    interval
5.  Verify the cluster health is restored after the process is restarted
    by typing

    .. code:: bash

       ceph -s

6.  Repeatedly kill monitor processes until error assertion occurs
7.  Ensure cluster health is restored after restart and alarm is cleared
8.  Ensure the monitor process cannot restart, e.g. move the ceph service
    to a different filename or kill the service, and then kill the monitor
    process.  Error assertion eventually takes place.
9.  Restore the service, and then repeat test on the other monitors
10.  Try killing multiple monitor processes at once.  The processes are
     restarted.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The ceph monitor processes should alarm when expected, and should recover
when killed.


~~~~~~~~~~~~~~~~
STOR_PROCESS_012
~~~~~~~~~~~~~~~~

:Test ID: STOR_PROCESS_012
:Test Title: test_ceph_osd_process_kill
:Tags: p1, storage, ceph, mtc, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to repeatedly kill the ceph osd process
and ensure they are restarted by the system.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System must have ceph-enabled

++++++++++
Test Steps
++++++++++

1.  Check the health of cluster by typing

    .. code:: bash

       ceph -s

    is ok.
2.  Query the osd tree via

    .. code:: bash

       ceph osd tree

    to see what osds are provisioned.
3.  Get the pid of the osds via

    .. code:: bash

       ps -ef | grep ceph

4.  Kill one of the osd pids via

    .. code:: bash

       sudo kill -9 <osd_pid>

    and verify the process is killed by running

    .. code:: bash

       ps -ef | grep ceph

5.  Verify the process is restarted by the system within the monitoring
    interval
6.  Verify the cluster health is restored after the process is restarted
    by typing

    .. code:: bash

       ceph -s

7.  Repeatedly kill osd processes until error assertion occurs.  Ensure
    the process is restarted automatically.
8.  Ensure cluster health is restored after restart and alarm is cleared
9.  Ensure the osd process cannot start, e.g. move the ceph service to a
    different filename or kill the ceph service, and then kill the osd process
10.  Ensure the error assertion eventually takes place.
11.  Restore the ceph service, and then kill all osd processes at once.
12.  Ensure all the processes are restarted
13.  Repeat this test on different node types

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The ceph osd processes should alarm when expected, and should recover
when killed.


~~~~~~~~~~~~~~~~~~~~
STOR_SCALABILITY_013
~~~~~~~~~~~~~~~~~~~~

:Test ID: STOR_SCALABILITY_013
:Test Title: test_ceph_8_node_system_basic_provisioning
:Tags: p1, storage, ceph, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to test the basic provisioning procedure for
8 storage node ceph systems.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- System must have 8 storage nodes available

++++++++++
Test Steps
++++++++++

1.  Provision an 8 storage node ceph-based system
2.  All nodes should become unlocked-enabled-available
3.  There should be no unexpected alarms, warnings or error
    conditions.
4.  There are no unexpected reboots or swacts during the installation
    procedure.
5.  The ceph cluster comes up with HEALTH_OK
6.  All expected OSDs are up
7.  Ensure the storage node pairing is correct.  storage-0 and storage-1
    will be in group-0, storage-2 and storage-3 should be in group-1 and so
    on.
8.  Validate the

    .. code:: bash

       ceph osd tree

    output is correct
9.  The placement group numbers should be scaled out (this occurs with
    greater than 3 storage nodes and more than 12 osds).  You can confirm
    this via:

    .. code:: bash

       ceph osd pool get cinder-volumes pg_num

    If there is at least 3 storage hosts and more than 12 osds, the pg_num
    can be greater than the default of 512. On a multi-storage node system
    it could be 1024 for
    example.
10.  Do some basic tests to confirm that the system is operating properly
     such as creating some large volumes, and creating VMs from those volumes.
     Perform some migrations, etc.
11.  Ensure that no issues are seen.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The system is properly configured and functioning as expected at the end
of the test.


~~~~~~~~~~~~
STOR_CORE_14
~~~~~~~~~~~~

:Test ID: STOR_CORE_014
:Test Title: test_ceph_node_reinstall
:Tags: p1, storage, ceph, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that host reinstall of nodes
running ceph-mon works properly on all supported configs.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- 2+X ceph system
- All-in-One Duplex ceph system
- Storage ceph system

++++++++++
Test Steps
++++++++++

1.  Lock one of the nodes that are part of a ceph-system.  e.g.
    controller-0 on an All-in-One Duplex system, controller-0 on a
    standard system, or storage-0 on a ceph storage system.
2.  Initiate a host re-install
3.  Ensure the host comes online after reinstall.
4.  Unlock the host
5.  Ensure the host eventually becomes available
6.  Check that ceph reports HEALTH_OK via

    .. code:: bash

       ceph -s

7.  Ensure the weights look accurate in

    .. code:: bash

       ceph osd tree

8.  Ensure there are no unexpected alarms or events
9.  Perform basic actions to ensure the system is working properly, e.g.
    create some volumes, import some images, launch VMs from volume.
10.  Repeat test for the other system configuration types

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Ceph should be healthy at the end of the test.


~~~~~~~~~~~~~
STOR_CORE_015
~~~~~~~~~~~~~

:Test ID: STOR_CORE_015
:Test Title: test_ceph_node_delete_and_reprovision
:Tags: p1, storage, ceph, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that host delete and reprovision
of nodes running ceph-mon works properly on all supported configs.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- 2+X ceph system
- All-in-One Duplex ceph system
- Storage ceph system

++++++++++
Test Steps
++++++++++

1.  Lock one of the nodes that are part of a ceph-system.  e.g.
    controller-0 on an All-in-One Duplex system, controller-0 on a
    standard system, or storage-0 on a ceph storage system.
2.  Delete the node
3.  Verify the appropriate alarms and events are seen.  Verify the ceph
    status is updated as expected.
4.  Re-provision the deleted node
5.  Once the node is available, ensure that ceph recovers.
6.  Ensure the weights look accurate in

    .. code:: bash

       ceph osd tree

7.  Ensure there are no unexpected alarms or events
8.  Perform basic actions to ensure the system is working properly, e.g.
    create some volumes, import some images, launch VMs from volume.
9.  Repeat test for the other system configuration types

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Ceph should be healthy at the end of the test.


~~~~~~~~~~~~~
STOR_CORE_016
~~~~~~~~~~~~~

:Test ID: STOR_CORE_016
:Test Title: test_lock_semantic_checks
:Tags: p1, storage, ceph, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that semantic checks with respect
to node lock, work properly on nodes running ceph monitors.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- 2+X ceph system  (ceph-mon on both controllers plus one worker node)
- All-in-One Duplex ceph system (ceph-mon on both controllers)
- Storage ceph system (ceph-mon on both controllers plus one storage node)
- All-in-One Simplex ceph system (ceph-mon on one controller)

++++++++++
Test Steps
++++++++++

1.  Lock one of the ceph monitor nodes in the system being tested
2.  Ensure

    .. code:: bash

       ceph -s

    reports HEALTH_WARN with one of the monitor's listed as being down
3.  Attempt to lock another one of the ceph monitors (if applies).
4.  Ensure this is rejected.
5.  Unlock the ceph monitor that was locked in step 1.
6.  Ensure ceph becomes healthy again.
7.  Repeat this for each node type, e.g. on a 2+X system, try this by
    locking the controller, and then do another test to lock the worker that
    is running the ceph monitor.
8.  Repeat test for each system type, e.g. 2+X, All-in-One Duplex,
    Storage, All-in-One Simplex.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Semantic checks should work as expected.


~~~~~~~~~~~~~
STOR_JOUR_017
~~~~~~~~~~~~~

:Test ID: STOR_JOUR_017
:Test Title: test_add_ssd_journal_function_to_existing_osds
:Tags: p1, storage, ceph, journals, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that the user can provision SSD
journals.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- 2+X ceph system  (ceph-mon on both controllers plus one worker node)
- All-in-One Duplex ceph system (ceph-mon on both controllers)
- Storage ceph system (ceph-mon on both controllers plus one storage node)
- All-in-One Simplex ceph system (ceph-mon on one controller)
- Spare disk(s) present to act as OSDs

++++++++++
Test Steps
++++++++++

1.  Provision an SSD disk with journal function

    .. code:: bash

       system host-stor-add --journal-location <location> --journal-size <GiB> --tier-uuid <UUID> <hostname>

2.  Assign --journal-location (using the SSD disk id) to every OSD via

    .. code:: bash

       system host-stor-update <osd_uuid> --journal-location <uuid> --journal-size <GiB>

3.  Check that the journal_node is updated for all OSDs
4.  Verify CEPH cluster health via

    .. code:: bash

       ceph -s

5.  Verify available of the ceph osd tree via

    .. code:: bash

       ceph osd tree

6.  Assign the journal function for each OSD as itself
7.  Verify the journal_node for each OSD points to itself
8.  Verify CEPH cluster health via

    .. code:: bash

       ceph -s

9.  Verify the output of

    .. code:: bash

       ceph osd tree

+++++++++++++++++
Expected Behavior
+++++++++++++++++

It should be possible to modify the journal configuration on the SSD
disks.


~~~~~~~~~~~
STOR_HW_018
~~~~~~~~~~~

:Test ID: STOR_HW_018
:Test Title: test_disk_replacement_osd_disk
:Tags: p1, storage, ceph, hw_replacement, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that the hardware disk replacement
procedure for OSDs is accurate.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Ideally this test would be run on all supported ceph configs: All-in-One
  Simplex, All-in-One Duplex, 2+X and Storage.
- Spare disks available for replacement tests.  The disks should be the
  same size or larger.  The disks should also be of the same type as the
  disk being replaced.

++++++++++
Test Steps
++++++++++

1.  Perform a disk replacement of the OSD disk using the customer
    documented procedure
2.  Ensure the replacement is successful and no unexpected alarms
    or events are seen
3.  Ensure the system operates normally after replacement, i.e. VMs can be
    launched, volumes can be created, existing VMs continue to function, etc.
4.  Ensure 'ceph osd tree' output is correct

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The system should be functional and healthy after hardware disk
replacement.


~~~~~~~~~~~
STOR_HW_019
~~~~~~~~~~~

:Test ID: STOR_HW_019
:Test Title: test_disk_replacement_journal_disk
:Tags: p1, storage, ceph, hw_replacement, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that the hardware disk replacement
procedure for journal disks is accurate.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Ideally this test would be run on all supported ceph configs: All-in-One
  Simplex, All-in-One Duplex, 2+X and Storage.
- Spare disks available for replacement tests.  The disks should be the
  same size or larger.  The disks should also be of the same type as the
  disk being replaced.

++++++++++
Test Steps
++++++++++

1.  Perform a disk replacement of the Journal disk using the customer
    documented procedure
2.  Ensure the replacement is successful and no unexpected alarms
    or events are seen
3.  Ensure the system operates normally after replacement, i.e. VMs can be
    launched, volumes can be created, existing VMs continue to function, etc.
4.  Ensure 'ceph osd tree' output is correct
5.  If the journal disk was used by OSDs, ensure the journal_node is
    updated as expected on the OSDs.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The system should be functional and healthy after hardware disk
replacement.


~~~~~~~~~~~
STOR_HW_020
~~~~~~~~~~~

:Test ID: STOR_HW_020
:Test Title: test_disk_replacement_nova_local_disk
:Tags: p1, storage, ceph, hw_replacement, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that the hardware disk replacement
procedure for nova local disks is accurate.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Ideally this test would be run on all supported configs: All-in-One Simplex,
  All-in-One Duplex, 2+X and Storage.
- Spare disks available for replacement tests.  The disks should be the
  same size or larger.  The disks should also be of the same type as the
  disk being replaced.

++++++++++
Test Steps
++++++++++

1.  Perform a disk replacement of a nova-local disk using the customer
    documented procedure
2.  Ensure the replacement is successful and no unexpected alarms
    or events are seen
3.  Ensure the system operates normally after replacement, i.e. VMs can be
    launched, volumes can be created, existing VMs continue to function, etc.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

The system should be functional and healthy after hardware disk
replacement.


~~~~~~~~~~~~~
STOR_PART_021
~~~~~~~~~~~~~

:Test ID: STOR_PART_021
:Test Title: test_host_partition_basic_tests
:Tags: p1, storage, ceph, partitions, regression

++++++++++++++
Test Objective
++++++++++++++

The objective of this test is to ensure that disk partition creation and
deletion behaviour is correct.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- There needs to be a disk on the system with some available space

++++++++++
Test Steps
++++++++++

1.  Create a partition via

    .. code::bash

       system host-disk-partition-add

2.  While the partition is being created, it will transition to 'Creating'
    state.  Once the partition is created, it will transition to 'Ready'
    state.
3.  Confirm partition list on a node

    .. code::bash

       system host-disk-partition-list --disk <disk uuid> controller-0

4.  Delete the Ready partition via:

    .. code:: bash

       system host-disk-partition-delete

5.  While the partition is being deleted, it will transition to 'Deleting'
    state before being Deleted
6.  Repeat partition creation but this time, attempt to delete the
    partition while it is in Creating state.
7.  This should be rejected.
8.  Create a new partition
9.  Modify the partition to be a larger size
10.  This will result in the partition being in 'Modifying' state
11.  Attempt to delete the partition while it is in Modifying state.  This
     should be rejected.
12.  Once the partition is done 'Modifying', it should go into 'Ready'
     state.

* Note, during the partition operations, you will see config out-of-date
  alarms raise and clear.  This is expected.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Partition creation and deletion should work as expected.


~~~~~~~~~~~~
STOR_DOR_022
~~~~~~~~~~~~

:Test ID: STOR_DOR_022
:Test Title: test_four_storage_node_dor_test
:Tags: p1, storage, ceph, dor, regression

++++++++++++++
Test Objective
++++++++++++++

To verify the system recovers after a DOR test (dead-office-recovery).

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- The system should have VMs running of various types (from volume and
  from image)
- Traffic should be running across VMs
- VMs should be writing to disk
- A ping should be done to all VMs
- Ceph should be healthy

++++++++++
Test Steps
++++++++++

1.  Write a simple shell script to bring down power to all nodes at once
2.  Power up all nodes at once (ideally through a script)
3.  Validate the system comes up alarm free
4.  Ensure that ping to VMs resumes
5.  Ensure the consoles of the VMs is accessible again
6.  Ensure that storage group provisioning is still accurate
7.  Ceph reports HEALTH_OK via 'ceph -s'

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Storage system recovers after DOR test


~~~~~~~~~~~~~~
STOR_FAULT_023
~~~~~~~~~~~~~~

:Test ID: STOR_FAULT_023
:Test Title: test_cable_pull_on_storage_system
:Tags: p1, storage, ceph, robustness, regression

++++++++++++++
Test Objective
++++++++++++++

To verify the system can recover when there is a cable pull on the cluster
network.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- The system should have VMs running of various types (from volume and
  from image)
- Traffic should be running across VMs
- VMs should be writing to disk
- A ping should be done to all VMs
- Ceph should be healthy

++++++++++
Test Steps
++++++++++

1.  Pull and then later replace the cluster network cable
2.  Ensure ping to VMs resumes
3.  Ensure consoles of VMs are accessible
4.  Ensure traffic is restored
5.  Verify ceph reports HEALTH_OK via

    .. code::bash

       ceph -s

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Storage system recovers after cable pull


~~~~~~~~~~~
STOR_FS_024
~~~~~~~~~~~

:Test ID: STOR_FS_024
:Test Title: test_ceph_filesystem_modification
:Tags: p1, storage, ceph, filesystem, regression

++++++++++++++
Test Objective
++++++++++++++

To verify that the sizes of the ceph pools can be modified.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++
- Any system configured with ceph

++++++++++
Test Steps
++++++++++

1.  Modify the ceph storage pools in Horizon
2.  Ensure the change is successful and the ceph pool size is updated via:

    .. code::bash

       ceph osd pool get-quota <poolname>

3.  Try setting one of the ceph pools to a value that is less than the
    data present in the pool.  You can confirm the data present via 'ceph df'.
    This should be rejected.
4.  Try to allocate the pools total to be more than the ceph pool total
    size.  This should not be possible.
5.  Try to set one of the pools to a really small value.
6.  Try to fill the pool.
7.  Ensure Ceph reports when the pool is full.
8.  Make sure you can clear the alarm by adjusting the pool size again.
9.  Repeat for the other ceph pools

+++++++++++++++++
Expected Behavior
+++++++++++++++++

It should be possible for the user to change the size of the ceph pools


~~~~~~~~~~~
STOR_VOL_25
~~~~~~~~~~~

:Test ID: STOR_VOL_025
:Test Title: test_instantiate_vm_with_large_volumes_and_live_migrate
:Tags: p1, storage, ceph, volumes, nova, regression

++++++++++++++
Test Objective
++++++++++++++

To verify migration works when VMs are booted from larger sized volumes.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system configured with ceph

++++++++++
Test Steps
++++++++++

1.  Create at least two large volumes (20GB, and 40GB)
2.  Boot VM
3.  Note boot time (for characterization) of VM (20 GB boot)
4.  Validate that VM boots, and that no timeouts or error status occur
5.  Log into VM, and validate that file system is read-write mode
6.  Boot second VM2 with larger volume
7.  Note boot time (for characterization) of VM2 (40 GB boot)
8.  Validate that VM2 boots, and that no timeouts or error status occur
9.  Log into VM2, and validate that file system is read-write mode
10.  Initiate live migration of VM and VM2
11.  Validate that VMs migrated, and no errors or alarms are present
12.  Log into both VMs and validate that file systems are read-write
13.  Terminate VMs

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Migration should work as expected


~~~~~~~~~~~~
STOR_VOL_026
~~~~~~~~~~~~

:Test ID: STOR_VOL_026
:Test Title: test_instantiate_vm_with_multiple_vol_attachments_and_migrate
:Tags: p1, storage, ceph, volumes, nova, regression

++++++++++++++
Test Objective
++++++++++++++

To verify migration works on VMs with multiple volume attachments

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system configured with ceph

++++++++++
Test Steps
++++++++++

1.  Create a volumes for boot and extra of at least 4 GB in size
2.  Boot VM
3.  Validate that VM boots, and that no timeouts or error status occur
4.  Add second volume to VM
5.  Initiate live migration of VM
6.  Validate that VM still has read-write access to both volumes
7.  Initiate a cold migration of VM
8.  Validate that VM still has read-write access to both volumes
9.  Evacuate the VM (reboot -f the worker)
10.  Validate that VM still has read-write access to both volumes
11.  Terminate VM

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Nova operations with multiple volume attachments work as expected


~~~~~~~~~~~~
STOR_VOL_027
~~~~~~~~~~~~

:Test ID: STOR_VOL_027
:Test Title: test_storage_node_recovery_failed_node
:Tags: p1, storage, ceph, volumes, nova, regression

++++++++++++++
Test Objective
++++++++++++++

To verify VMs can continue to write to volumes when there is a storage
node failure.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system configured with ceph

++++++++++
Test Steps
++++++++++

1.  Create a volume for boot at least 40 GB in size
2.  Boot VM
3.  Validate that VMs boot, and that no timeouts or error status occur
4.  Start filesystem write operation on VM.  You can use dd.
5.  Reboot one of the storage nodes via

    .. code::bash

       sudo reboot -f

6.  Validate VMs still has read-write access to volumes, and note
    filesystem outage time
7.  Terminate VM
8.  Verify the storage node eventually recovers

+++++++++++++++++
Expected Behavior
+++++++++++++++++

VMs continue to write to disk despite storage node failure


~~~~~~~~~~~~~
STOR_CORE_028
~~~~~~~~~~~~~

:Test ID: STOR_CORE_028
:Test Title: test_convert_between_storage_types
:Tags: p1, storage, ceph, regression

++++++++++++++
Test Objective
++++++++++++++

This test validates that the user can convert between different storage
types.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system configured with ceph
- Any system that has more than 2 nodes for hosting VMs
- System is setup for remote storage
- Some VMs exist at the start of test (if not, create them)

++++++++++
Test Steps
++++++++++

1.  Lock a worker that is hosting VMs.  On lock, all VMs should be
    migrated off.
2.  Modify the worker nova-local backend from remote storage to image.
3.  Unlock the worker
4.  Ensure it is possible to schedule new VMs on the image-backed nodes.
5.  Repeat in the opposite direction, e.g. image to remote.

+++++++++++++++++
Expected Behavior
+++++++++++++++++

It should be possible to modify the nova-local backend


~~~~~~~~~~~~~
STOR_PROF_029
~~~~~~~~~~~~~

:Test ID: STOR_PROF_029
:Test Title: test_storage_profiles
:Tags: p1, storage, ceph, regression

++++++++++++++
Test Objective
++++++++++++++

This test validates the creation and application of storage profiles on a
system.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any ceph based system

++++++++++
Test Steps
++++++++++

1.  Create a storage profile of a nova-local remote host
2.  Ensure the profile is created successfully
3.  Reinstall a node of the same type
4.  Ensure you can apply the storage profile to the node
5.  Complete provisioning of the node
6.  Ensure it comes up successfully
7.  Ensure you can host VMs on it

+++++++++++++++++
Expected Behavior
+++++++++++++++++

It should be possible to apply an existing storage profile to a new node


~~~~~~~~~~~~~
STOR_PART_030
~~~~~~~~~~~~~

:Test ID: STOR_PART_030
:Test Title: test_creation_deletion_of_multiple_partitions_and_semantic_checks
:Tags: p1, storage, ceph, partitions, regression

++++++++++++++
Test Objective
++++++++++++++

This test validates that multiple partitions can be created and the
partition modification/deletion behaviour is correct.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Disk exists with some unallocated space

++++++++++
Test Steps
++++++++++

1.  Create multiple partitions allowing time for the partition to get to
    Ready state prior to creating the next one.
2.  Attempt creating multiple partitions at the same time ie. while one is
    still in Modifying state. Semantic check should not allow this and
    appropriate feedback should be provided.
3.  Validate that only the last partition can be modified (for example add
    9+ partitions and confirm on the last partition can be edited)
4.  Validate only the last partition can be deleted
5.  After deletion, ensure the new last partition can be modified/deleted

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Partition creation, deletion and semantic checks should work as expected.


~~~~~~~~~~~~
STOR_VOL_031
~~~~~~~~~~~~

:Test ID: STOR_VOL_031
:Test Title: test_instantiate_vm_with_large_volumes_and_cold_migrate
:Tags: p1, storage, ceph, volumes, nova, regression

++++++++++++++
Test Objective
++++++++++++++

To verify migration works when VMs are booted from larger sized volumes.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system configured with ceph

++++++++++
Test Steps
++++++++++

1.  Create at least two large volumes (20GB, and 40GB)
2.  Boot VM
3.  Validate that VM boots, and that no timeouts or error status occur
4.  Log into VM, and validate that file system is read-write mode
5.  Boot second VM2 with larger volume
6.  Validate that VM2 boots, and that no timeouts or error status occur
7.  Log into VM2, and validate that file system is read-write mode
8.  Initiate cold migration of VM and VM2
9.  Validate that VMs migrated, and no errors or alarms are present
10.  Log into both VMs and validate that file systems are read-write
11.  Terminate VMs

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Migration should work as expected


~~~~~~~~~~~~
STOR_VOL_032
~~~~~~~~~~~~

:Test ID: STOR_VOL_032
:Test Title: test_instantiate_vm_with_large_volumes_and_evacuate
:Tags: p1, storage, ceph, volumes, nova, regression

++++++++++++++
Test Objective
++++++++++++++

To verify evacuation works as expected when VMs are booted from larger
size volumes.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system configured with ceph

++++++++++
Test Steps
++++++++++

1.  Create at least two large volumes (20GB, and 40GB)
2.  Boot VM
3.  Validate that VM boots, and that no timeouts or error status occur
4.  Log into VM, and validate that file system is read-write mode
5.  Boot second VM2 with larger volume
6.  Validate that VM2 boots, and that no timeouts or error status occur
7.  Log into VM2, and validate that file system is read-write mode
8.  Initiate live migration VMs as needed to coral them onto a single worker
9.  Once VMs are on a single worker, reboot (reboot -f) the worker to
    initiate an evacuations
10.  Validate that VMs evacuated, and no errors or alarms are present
11.  Log into both VMs and validate that file systems are read-write
12.  Terminate VMs

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Evacuation should work as expected


~~~~~~~~~~~
STOR_FS_033
~~~~~~~~~~~

:Test ID: STOR_FS_033
:Test Title: test_modify_ceph_mon
:Tags: p1, storage, ceph, filesystem, regression

++++++++++++++
Test Objective
++++++++++++++

To ensure that the size of ceph-mon can be increased.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

- Any system with ceph-enabled

++++++++++
Test Steps
++++++++++

1.  Run the following command:

    .. code::bash

       system ceph-mon-modify <node> ceph_mon_gib=<value>

2.  Ensure the size of ceph mon is changed on the controllers via 'df':


    .. code::bash

       Filesystem                                1K-blocks     Used Available Use% Mounted on
       /dev/sda3                                  20027216  9400392   9586440 50%  /
       devtmpfs                                   65851888        0  65851888 0%   /dev
       tmpfs                                      65870796      580  65870216 1%   /dev/shm
       tmpfs                                      65870796    15160  65855636 1%   /run
       tmpfs                                      65870796        0  65870796 0%   /sys/fs/cgroup
       tmpfs                                       1048576      180   1048396 1%   /tmp
       /dev/mapper/cgts--vg-gnocchi--lv            4947584    20560   4648496 1%   /opt/gnocchi
       /dev/mapper/cgts--vg-img--conversions--lv  20511312    45084  19401268 1%   /opt/img-conversions
       /dev/mapper/cgts--vg-scratch--lv            8126904    51364   7639728 1%   /scratch
       /dev/mapper/cgts--vg-backup--lv            51474912    53272  48783816 1%   /opt/backups
       /dev/mapper/cgts--vg-ceph--mon--lv         20511312    65832  19380520 1%   /var/lib/ceph/mon

+++++++++++++++++
Expected Behavior
+++++++++++++++++
The size should be increased on both controllers

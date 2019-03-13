==================
Backup and Restore
==================

This test plan covers test cases for the fundamental functionalities of
Backup and Restore.
It includes basic functionality for the following features:

- Backup and Restore for an All-in-One Simplex system
- Backup and Restore for an All-in-One Duplex system
- Backup and Restore for a system with dedicated storage nodes
- Backup and Restore for a system configured with Ipv6
- Backup and Restore for a system with HTTPS enabled
- Validate the system with sanity test suite after Restore

--------------------
Overall Requirements
--------------------
This test will require access to the following configurations:

- enough space for controllerfs 'backup' (ref. to user manuals for details)
- external storage media to save the backup files
- bootable USB or PXE Boot infrastructure (ref. to user manuals for details)

----------
Test Cases
----------

.. contents::
   :local:
   :depth: 1

~~~~~~~~~~~~
BNR_AIOSX_01
~~~~~~~~~~~~

:Test ID: BNR_AIOSX_01
:Test Title: test_backup_and_restore_all_in_one_simplex
:Tags: p1, automatated, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

The objective of this test is to ensure that an All-in-One Simplex system can
be successfully backed up and restored on the same hardware.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

The system to test is a healthy All-in-One Simplex:
- no active alarms
- no VMs in 'Error'

++++++++++
Test Steps
++++++++++

1.  launch VMs

2.  Backup System and Images:

    .. code:: bash

        sudo config_controller --backup <backup_name>

3.  Backing Up Available Cinder Volumes

    .. code:: bash

        cinder backup-create --name <backup_name> --container cinder <vol_uuid>

4.  Backing Up In-Use Cinder Volumes

    .. code:: bash

        cinder snapshot-create --force True \
            --display-name <snapshot_name> <vol_uuid>
        cinder backup-create --name <backup_name> \
            --snapshot-id <snapshot_id> --container cinder

5.  install the lab with the same load (better first to wipe the contents
    of disks of the system)

6.  Restore the system configuration

    .. code:: bash

        sudo config_controller --restore-system <backup_name_system.tgz>

7.  Lock any (except the current/active controller) unlocked nodes
    Using force lock if needed

8.  Restore the system images.

    .. code:: bash

        sudo config_controller --restore-images <backup_name_images.tgz>

9.  Restore Cinder volumes if Storage nodes are included in Backup and Restore
    -restore 'available' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>

    -restore 'in-use' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        cinder reset-state --state available <volume-uuid>
        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>
        cinder reset-state --state in-use <volume-uuid>

10. Complete the restore

    .. code:: bash

        sudo config_controller --restore-complete

11. Restore controller-1
    -power on
    -unlock

+++++++++++++++++
Expected Behavior
+++++++++++++++++

- All Backup and Restore procedures completed without any issues
- Restored system is working without any issues and all VMs are restored

~~~~~~~~~~~~
BNR_AIODX_01
~~~~~~~~~~~~

:Test ID: BNR_AIODX_01
:Test Title: backup_and_restore_a_all_in_one_deplux_lab
:Tags: p1, automated, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

The objective of this test is to ensure that an All-in-One Duplex system can
be successfully backed up and restored on the same hardware.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

The system to test is a healthy All-in-One Duplex:
- no active alarms
- no VMs in 'Error'

++++++++++
Test Steps
++++++++++

1.  launch VMs

2.  Backup System and Images:

    .. code:: bash

        sudo config_controller --backup <backup_name>

3.  Backing Up Available Cinder Volumes

    .. code:: bash

        cinder backup-create --name <backup_name> \
            --container cinder <volume_uuid>

4.  Backing Up In-Use Cinder Volumes

    .. code:: bash

        cinder snapshot-create --force True \
            --display-name <snapshot_name> <volume_uuid>
        cinder backup-create --name <backup_name> \
            --snapshot-id <snapshot_id> --container cinder

5.  install the lab with the same load (better first to wipe the contents
    of disks of the system)

6.  Restore the system configuration

    .. code:: bash

        sudo config_controller --restore-system <backup_name_system.tgz>

7.  Restore the system images.

    .. code:: bash

        sudo config_controller --restore-images <backup_name_images.tgz>

8.  Restore Cinder volumes if Storage nodes are included in Backup and Restore
    -restore 'available' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>

    -restore 'in-use' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        cinder reset-state --state available <volume-uuid>
        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>
        cinder reset-state --state in-use <volume-uuid>

9. Complete the restore

    .. code:: bash

        sudo config_controller --restore-complete

+++++++++++++++++
Expected Behavior
+++++++++++++++++

- All Backup and Restore procedures completed without any issues
- Restored system is working without any issues and all VMs are restored

~~~~~~~~~~
BNR_IP6_01
~~~~~~~~~~

:Test ID: BNR_IP6_01
:Test Title: backup_and_restore_a_ip-v6_lab
:Tags: p1, automated, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

The objective of this test is to ensure that an IPv6 system can
be successfully backed up and restored on the same hardware.


+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

The system to test is provisioned with IPv6

++++++++++
Test Steps
++++++++++

1.  launch VMs

2.  Backup System and Images:

    .. code:: bash

        sudo config_controller --backup <backup_name>

3.  Backing Up Available Cinder Volumes

    .. code:: bash

        cinder backup-create --name <backup_name> \
            --container cinder <volume_uuid>

4.  Backing Up In-Use Cinder Volumes

    .. code:: bash

        cinder snapshot-create --force True \
            --display-name <snapshot_name> <volume_uuid>
        cinder backup-create --name <backup_name> \
            --snapshot-id <snapshot_id> --container cinder

5.  install the lab with the same load (better first to wipe the contents
    of disks of the system)

6.  Restore the system configuration

    if CEPH is not included (By default):

    .. code:: bash

        sudo config_controller --restore-system exclude-storage-reinstall \
            <backup-file>

    if CEPH is included:

    .. code:: bash

        sudo config_controller --restore-system include-storage-reinstall \
            <backup-file>

7.  Restore the system images.

    .. code:: bash

        sudo config_controller --restore-images <backup_name_images.tgz>

8.  Restore Cinder volumes if Storage nodes are included in Backup and Restore
    -restore 'available' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>

    -restore 'in-use' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        cinder reset-state --state available <volume-uuid>
        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>
        cinder reset-state --state in-use <volume-uuid>

9. Run sudo config_controller --restore-complete

10. Restore controller-1
    -power on
    -unlock

11. Restore other storage and compute nodes if applicable

+++++++++++++++++
Expected Behavior
+++++++++++++++++

- All Backup and Restore procedures completed without any issues
- Restored system is working without any issues and all VMs are restored

~~~~~~~~~~~~~~
BNR_STORAGE_01
~~~~~~~~~~~~~~

:Test ID: BNR_STORAGE_01
:Test Title: backup_and_restore_a_storage_lab
:Tags: p1, automated, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

The objective of this test is to ensure that a system  with dedicated storage
 nodes can be successfully backed up and restored on the same hardware.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++


The system to test is a healthy All-in-One Simplex:
- no active alarms
- no VMs in 'Error'

++++++++++
Test Steps
++++++++++


1.  launch VMs

2.  Backup System and Images:

    .. code:: bash

        sudo config_controller --backup <backup_name>

3.  Backing Up Available Cinder Volumes

    .. code:: bash

        cinder backup-create --name <backup_name> \
            --container cinder <volume_uuid>

4.  Backing Up In-Use Cinder Volumes

    .. code:: bash

        cinder snapshot-create --force True \
            --display-name <snapshot_name> <volume_uuid>
        cinder backup-create --name <backup_name> \
            --snapshot-id <snapshot_id> --container cinder

5.  install the lab with the same load (better first to wipe the contents
        of disks of the system)

6.  Restore the system configuration
    if CEPH is not included (By default):

    .. code:: bash

        sudo config_controller --restore-system exclude-storage-reinstall \
            <backup-file>

    if CEPH is included:

    .. code:: bash

        sudo config_controller --restore-system include-storage-reinstall \
            <backup-file>

7.  Restore the system images.
    sudo config_controller --restore-images <backup_name_images.tgz>

8.  Restore Cinder volumes if Storage nodes are included in Backup and Restore
    -restore 'available' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>

    -restore 'in-use' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        cinder reset-state --state available <volume-uuid>
        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>
        cinder reset-state --state in-use <volume-uuid>

9. Complete the restore

    .. code:: bash

        sudo config_controller --restore-complete

10. Restore controller-1
    -power on
    -unlock

11. Restore other storage and compute nodes

+++++++++++++++++
Expected Behavior
+++++++++++++++++

- All Backup and Restore procedures completed without any issues
- Restored system is working without any issues and all VMs are restored

~~~~~~~~~~~~~~~
BNR_SECURITY_01
~~~~~~~~~~~~~~~

:Test ID: BNR_SECURITY_01
:Test Title: verify_backup_restore_works_on_https_lab
:Tags: p1, automated, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

The objective of this test is to ensure that an All-in-One Simplex system can
be successfully backed up and restored on the same hardware.


+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

The system to test is provisioned with HTTPS

++++++++++
Test Steps
++++++++++
1.  launch VMs

2.  Backup System and Images:

    .. code:: bash

        sudo config_controller --backup <backup_name>

3.  Backing Up Available Cinder Volumes

    .. code:: bash

        cinder backup-create --name <backup_name> \
            --container cinder <volume_uuid>

4.  Backing Up In-Use Cinder Volumes

    .. code:: bash

        cinder snapshot-create --force True \
            --display-name <snapshot_name> <volume_uuid>
        cinder backup-create --name <backup_name> \
            --snapshot-id <snapshot_id> --container cinder

5.  install the lab with the same load (better first to wipe the contents
        of disks of the system)

6.  Restore the system configuration
    if CEPH is not included (By default):

    .. code:: bash

        sudo config_controller --restore-system exclude-storage-reinstall \
            <backup-file>

    if CEPH is included:

    .. code:: bash

        sudo config_controller --restore-system include-storage-reinstall \
            <backup-file>

7.  Restore the system images.

    .. code:: bash

        sudo config_controller --restore-images <backup_name_images.tgz>

8.  Restore Cinder volumes if Storage nodes are included in Backup and Restore
    -restore 'available' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>

    -restore 'in-use' volumes
    --change to root
    --copy files into designated directory

    .. code:: bash

        cinder reset-state --state available <volume-uuid>
        rbd create --pool cinder-volumes --image <volume-uuid> --size 3G
        cinder backup-list
        cinder backup-restore --volume <volume-uuid> <backup-uuid>
        cinder reset-state --state in-use <volume-uuid>

9. Run sudo config_controller --restore-complete

10. Restore controller-1
    -power on
    -unlock

11. Restore other storage and compute nodes if applicable

+++++++++++++++++
Expected Behavior
+++++++++++++++++

- All Backup and Restore procedures completed without any issues
- Restored system is working without any issues and all VMs are restored

~~~~~~~~~~~~
BNR_SYS_01
~~~~~~~~~~~~

:Test ID: BNR_SYS_01
:Test Title: validate_sanity_suite_after_a_restore
:Tags: p1, automated, regression

++++++++++++++++++
Testcase Objective
++++++++++++++++++

The objective of this test is to ensure that fundamental features of system
are working.

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

The system is restored successfully

++++++++++
Test Steps
++++++++++

    1.  Run Sanity suites

+++++++++++++++++
Expected Behavior
+++++++++++++++++

    1.  All test cases in Sanity suites pass

----------
References
----------

=======================
Appropriate File Access
=======================

.. contents::
   :local:
   :depth: 1

-----------------------------
SECURITY_Appro_File_Access_01
-----------------------------

:Test ID: SECURITY_Appro_File_Access_01
:Test Title: File permission after initial install.
:Tags: Security

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify "opt/platform" and "etc/(system)-config" file permission after initial
install.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

New Starlingx configuration lab install with all nodes up and running.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to active controller and make sure that all config files have at least
this kind of permission by root ""-rw-r--r--"". If there are some other config
files with less permissions is ok.

.. code:: bash

   $ ls -la /etc/*.conf
   i.e.
   controller-0:/etc$ ls -la /etc/*.conf
     -rw-r--r--. 1 root root   55 Apr 10  2018 /etc/asound.conf
     -rw-r--r--  1 root root 3661 Feb  8 15:23 /etc/collectd.conf
     -rw-r-----  1 root root 2643 Feb  8 15:23 /etc/dnsmasq.conf
     -rw-r--r--. 1 root root 1285 Apr 11  2018 /etc/dracut.conf
     -rw-r-----  1 root root   71 Feb  8 15:19 /etc/drbd.conf
     ...

2. Go to active controller and make sure that /opt/platform/* files have
following permission (If there are some other files with less permissions is
ok), use following command to get /opt/platform file tree.

.. code:: bash

  i.e.
  controller-0:/opt/platform# ls -R | grep "":$"" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/   /' -e 's/-/|/'
  |-config
  |---18.10
  |-----branding
  |-----postgresql
  |-----pxelinux.cfg
  |-----ssh_config
  |-lost+found
  |-nfv
  |---vim
  |-----18.10
  |-puppet
  |---18.10
  |-----hieradata
  |-sysinv
  |---18.10

Use the following command to get all file permissions.

.. code:: bash

  i.e.
  controller-0:/opt/platform# ls -ll -R
  .:
  total 32
  drwxr-xr-x 3 root   root  4096 Feb  8 15:20 config
  -rw-r--r-- 1 root   root     0 Feb 11 13:09 files.txt
  drwx------ 2 root   root 16384 Feb  8 15:19 lost+found
  drwxr-xr-x 3 root   root  4096 Feb  8 15:32 nfv
  drwxr-xr-x 3 root   root  4096 Feb  8 15:20 puppet
  drwxr-xr-x 3 sysinv root  4096 Feb  8 15:20 sysinv

  ./config:
  total 4
  drwxr-xr-x 6 root root 4096 Feb  8 15:54 18.10

  ./config/18.10:
  total 44
  drwxr-xr-x 2 root root 4096 Feb  8 15:20 branding
  -rw-r--r-- 1 root root 1895 Feb  8 15:18 cgcs_config
  -rw-r--r-- 1 root root  338 Feb  8 15:43 dnsmasq.addn_hosts
  -rw-r--r-- 1 root root    1 Feb  8 15:20 dnsmasq.addn_hosts_dc
  -rw-r--r-- 1 root root  338 Feb  8 16:03 dnsmasq.addn_hosts.temp
  -rw-r--r-- 1 root root  222 Feb  8 15:54 dnsmasq.hosts
  -rw-r--r-- 1 root root  222 Feb  8 16:03 dnsmasq.hosts.temp
  -rw-r--r-- 1 root root    0 Feb  9 16:04 dnsmasq.leases
  -rw-r--r-- 1 root root  526 Feb  8 15:30 hosts
  drwxr-xr-x 2 root root 4096 Feb  8 15:20 postgresql
  drwxr-xr-x 2 root root 4096 Feb  8 16:03 pxelinux.cfg
  drwxr-xr-x 2 root root 4096 Feb  8 15:18 ssh_config

  ./config/18.10/branding:
  total 4
  -rwxr-xr-x 1 root root 525 Oct  3 14:37 horizon-region-exclusions.csv

  ./config/18.10/postgresql:
  total 28
  -rw-r----- 1 postgres postgres   929 Feb  8 15:19 pg_hba.conf
  -rw-r----- 1 postgres postgres    47 Feb  8 15:19 pg_ident.conf
  -rw------- 1 postgres postgres 20195 Feb  8 15:19 postgresql.conf

  ./config/18.10/pxelinux.cfg:
  total 16
  -rw-r--r-- 1 root root 861 Feb  8 16:03 01-52-54-00-c8-5c-10
  -rw-r--r-- 1 root root 939 Feb  8 15:46 01-52-54-00-c8-84-5c
  lrwxrwxrwx 1 root root  35 Feb  8 15:31 default -> /pxeboot/pxelinux.cfg.files/default
  -rw-r--r-- 1 root root 684 Feb  8 16:03 efi-01-52-54-00-c8-5c-10
  -rw-r--r-- 1 root root 762 Feb  8 15:46 efi-01-52-54-00-c8-84-5c
  lrwxrwxrwx 1 root root  36 Feb  8 15:31 grub.cfg -> /pxeboot/pxelinux.cfg.files/grub.cfg

  ./config/18.10/ssh_config:
  total 16
  -rw------- 1 root root 1679 Feb  8 15:18 nova_migration_key
  -rw-r--r-- 1 root root  396 Feb  8 15:18 nova_migration_key.pub
  -rw------- 1 root root  227 Feb  8 15:18 system_host_key
  -rw-r--r-- 1 root root  176 Feb  8 15:18 system_host_key.pub

  ./lost+found:
  total 0

  ./nfv:
  total 4
  drwxr-xr-x 3 root root 4096 Feb  8 15:32 vim

  ./nfv/vim:
  total 4
  drwxr-xr-x 2 root root 4096 Feb  8 15:54 18.10

  ./nfv/vim/18.10:
  total 1112
  -rw-r--r-- 1 root root   49152 Feb 11 13:03 vim_db_v1
  -rw-r--r-- 1 root root   32768 Feb 11 13:08 vim_db_v1-shm
  -rw-r--r-- 1 root root 1049080 Feb 11 13:08 vim_db_v1-wal

  ./puppet:
  total 4
  drwxr-xr-x 3 root root 4096 Feb  8 15:20 18.10

  ./puppet/18.10:
  total 4
  drwxr-xr-x 2 root root 4096 Feb  8 16:03 hieradata

  ./puppet/18.10/hieradata:
  total 92
  -rw------- 1 root root  9627 Feb  8 15:54 192.168.204.3.yaml
  -rw------- 1 root root  9620 Feb  8 16:03 192.168.204.4.yaml
  -rw------- 1 root root  8494 Feb  8 15:18 secure_static.yaml
  -rw------- 1 root root  3196 Feb  8 16:03 secure_system.yaml
  -rw------- 1 root root  1968 Feb  8 15:18 static.yaml
  -rw------- 1 root root 45299 Feb  8 16:03 system.yaml

  ./sysinv:
  total 4
  drwxr-xr-x 2 sysinv root 4096 Feb  8 15:26 18.10

  ./sysinv/18.10:
  total 4
  -rw-r--r-- 1 root root 1505 Feb  8 15:26 sysinv.conf.default

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. All ``ls -la /etc/*.conf`` config files have at least -rw-r--r-- permissions.

2. All /opt/platform files have proper permissions.

-----------------------------
SECURITY_Appro_File_Access_02
-----------------------------

:Test ID: SECURITY_Appro_File_Access_02
:Test Title: File permission after reboot nodes.
:Tags: Security

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Verify "opt/platform" and "etc/(system)-config" file permission after reboot
nodes.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

Any Starlingx configuration lab with all nodes rebooted, up and running.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Go to active controller and make sure that all config files have at least
this kind of permission by root ""-rw-r--r--"". If there are some other config
files with less permissions is ok.

.. code:: bash

  $ ls -la /etc/*.conf
  i.e.

  controller-0:/etc$ ls -la /etc/*.conf
  -rw-r--r--. 1 root root   55 Apr 10  2018 /etc/asound.conf
  -rw-r--r--  1 root root 3661 Feb  8 15:23 /etc/collectd.conf
  -rw-r-----  1 root root 2643 Feb  8 15:23 /etc/dnsmasq.conf
  -rw-r--r--. 1 root root 1285 Apr 11  2018 /etc/dracut.conf
  -rw-r-----  1 root root   71 Feb  8 15:19 /etc/drbd.conf
  ...

2. Go to active controller and make sure that /opt/platform/* files have
following permission (If there are some other files with less permissions is
ok), use following command to get /opt/platform file tree.

.. code:: bash

  i.e.

  controller-0:/opt/platform# ls -R | grep "":$"" | sed -e 's/:$//' -e 's/[^-][^\/]*\//--/g' -e 's/^/   /' -e 's/-/|/'
   .
   |-config
   |---18.10
   |-----branding
   |-----postgresql
   |-----pxelinux.cfg
   |-----ssh_config
   |-lost+found
   |-nfv
   |---vim
   |-----18.10
   |-puppet
   |---18.10
   |-----hieradata
   |-sysinv
   |---18.10

   Use the following command to get all file permissions.
   i.e.
   controller-0:/opt/platform# ls -ll -R
  .:
  total 32
  drwxr-xr-x 3 root   root  4096 Feb  8 15:20 config
  -rw-r--r-- 1 root   root     0 Feb 11 13:09 files.txt
  drwx------ 2 root   root 16384 Feb  8 15:19 lost+found
  drwxr-xr-x 3 root   root  4096 Feb  8 15:32 nfv
  drwxr-xr-x 3 root   root  4096 Feb  8 15:20 puppet
  drwxr-xr-x 3 sysinv root  4096 Feb  8 15:20 sysinv

  ./config:
  total 4
  drwxr-xr-x 6 root root 4096 Feb  8 15:54 18.10

  ./config/18.10:
  total 44
  drwxr-xr-x 2 root root 4096 Feb  8 15:20 branding
  -rw-r--r-- 1 root root 1895 Feb  8 15:18 cgcs_config
  -rw-r--r-- 1 root root  338 Feb  8 15:43 dnsmasq.addn_hosts
  -rw-r--r-- 1 root root    1 Feb  8 15:20 dnsmasq.addn_hosts_dc
  -rw-r--r-- 1 root root  338 Feb  8 16:03 dnsmasq.addn_hosts.temp
  -rw-r--r-- 1 root root  222 Feb  8 15:54 dnsmasq.hosts
  -rw-r--r-- 1 root root  222 Feb  8 16:03 dnsmasq.hosts.temp
  -rw-r--r-- 1 root root    0 Feb  9 16:04 dnsmasq.leases
  -rw-r--r-- 1 root root  526 Feb  8 15:30 hosts
  drwxr-xr-x 2 root root 4096 Feb  8 15:20 postgresql
  drwxr-xr-x 2 root root 4096 Feb  8 16:03 pxelinux.cfg
  drwxr-xr-x 2 root root 4096 Feb  8 15:18 ssh_config

  ./config/18.10/branding:
  total 4
  -rwxr-xr-x 1 root root 525 Oct  3 14:37 horizon-region-exclusions.csv

  ./config/18.10/postgresql:
  total 28
  -rw-r----- 1 postgres postgres   929 Feb  8 15:19 pg_hba.conf
  -rw-r----- 1 postgres postgres    47 Feb  8 15:19 pg_ident.conf
  -rw------- 1 postgres postgres 20195 Feb  8 15:19 postgresql.conf

  ./config/18.10/pxelinux.cfg:
  total 16
  -rw-r--r-- 1 root root 861 Feb  8 16:03 01-52-54-00-c8-5c-10
  -rw-r--r-- 1 root root 939 Feb  8 15:46 01-52-54-00-c8-84-5c
  lrwxrwxrwx 1 root root  35 Feb  8 15:31 default -> /pxeboot/pxelinux.cfg.files/default
  -rw-r--r-- 1 root root 684 Feb  8 16:03 efi-01-52-54-00-c8-5c-10
  -rw-r--r-- 1 root root 762 Feb  8 15:46 efi-01-52-54-00-c8-84-5c
  lrwxrwxrwx 1 root root  36 Feb  8 15:31 grub.cfg -> /pxeboot/pxelinux.cfg.files/grub.cfg

  ./config/18.10/ssh_config:
  total 16
  -rw------- 1 root root 1679 Feb  8 15:18 nova_migration_key
  -rw-r--r-- 1 root root  396 Feb  8 15:18 nova_migration_key.pub
  -rw------- 1 root root  227 Feb  8 15:18 system_host_key
  -rw-r--r-- 1 root root  176 Feb  8 15:18 system_host_key.pub

  ./lost+found:
  total 0

  ./nfv:
  total 4
  drwxr-xr-x 3 root root 4096 Feb  8 15:32 vim

  ./nfv/vim:
  total 4
  drwxr-xr-x 2 root root 4096 Feb  8 15:54 18.10

  ./nfv/vim/18.10:
  total 1112
  -rw-r--r-- 1 root root   49152 Feb 11 13:03 vim_db_v1
  -rw-r--r-- 1 root root   32768 Feb 11 13:08 vim_db_v1-shm
  -rw-r--r-- 1 root root 1049080 Feb 11 13:08 vim_db_v1-wal

  ./puppet:
  total 4
  drwxr-xr-x 3 root root 4096 Feb  8 15:20 18.10

  ./puppet/18.10:
  total 4
  drwxr-xr-x 2 root root 4096 Feb  8 16:03 hieradata

  ./puppet/18.10/hieradata:
  total 92
  -rw------- 1 root root  9627 Feb  8 15:54 192.168.204.3.yaml
  -rw------- 1 root root  9620 Feb  8 16:03 192.168.204.4.yaml
  -rw------- 1 root root  8494 Feb  8 15:18 secure_static.yaml
  -rw------- 1 root root  3196 Feb  8 16:03 secure_system.yaml
  -rw------- 1 root root  1968 Feb  8 15:18 static.yaml
  -rw------- 1 root root 45299 Feb  8 16:03 system.yaml

  ./sysinv:
  total 4
  drwxr-xr-x 2 sysinv root 4096 Feb  8 15:26 18.10

  ./sysinv/18.10:
  total 4
  -rw-r--r-- 1 root root 1505 Feb  8 15:26 sysinv.conf.default

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. All ``"ls -la /etc/*.conf"`` config files have at least "-rw-r--r--"
permissions.

2. All /opt/platform files have proper permissions.

-----------------------------
SECURITY_Appro_File_Access_03
-----------------------------

:Test ID: SECURITY_Appro_File_Access_03
:Test Title: bash.log behaviour on node.
:Tags: Security

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Validate bash.log behavior on node.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

At least 1 Controller + 1 compute + 1 Storage

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. On node type:

.. code:: bash

  $ sudo lsattr /var/log/bash.log

and confirm that bash.log is set to append only.

.. code:: bash

  -----a-------e-- bash.log <-- append-only attr on

2- On node type

.. code:: bash

  $ sudo lsattr /var/log/user.log

and confirm that bash.log is set to append only.

.. code:: bash

  -------------e-- user.log <-- append-only attr off""

3- Attempt to edit bash.log, modify the existing data and save the file.

.. code:: bash

  $ sudo vim /var/log/bash.log

::
  Hit ´i´ to change to INSERT mode
  Edit the file
  Hit Escape, :wq! ""

4- Attempt to remove the append-only attribute of bash.log

.. code:: bash

  $ sudo chattr -a bash.log in order to

**Repeat steps on a compute and storage nodes.**

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

* Confirm append-only attribute ON of bash.log

* Confirm append-only attribute OFF of user.log

* Validate that this is blocked and system gets back with

.. code:: bash

  "/var/log/bash.log ERROR:: Can´t open file for writing remove the append-only attribute."

* Validate this is rejected.

* Steps validated on compute and storage nodes.

~~~~~~~~~~~
References:
~~~~~~~~~~~

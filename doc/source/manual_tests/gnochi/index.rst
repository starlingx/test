=======
GNOCCHI
=======

Gnocchi is an open-source time series database, the problem that Gnocchi solves is the storage and
indexing of time series data and resources at a large scale. This is useful in modern cloud
platforms which are not only huge but also are dynamic and potentially multi-tenant. Gnocchi takes
all of that into account. Gnocchi has been designed to handle large amounts of aggregates being
stored while being performant, scalable and fault-tolerant. While doing this, the goal was to be
sure to not build any hard dependency on any complex storage system.
Gnocchi takes a unique approach to time series storage: rather than storing raw data points, it
aggregates them before storing them. This built-in feature is different from most other time series
databases, which usually support this mechanism as an option and compute aggregation
(average, minimum, etc.) at query time. Because Gnocchi computes all the aggregations at ingestion
getting the data back is extremely fast, as it just needs to read back the pre-computed results.


--------------------
Overall Requirements
--------------------

StarlingX environment setup

----------
Test Cases
----------


.. contents::
   :local:
   :depth: 1

~~~~~~~~~~
Gnocchi_01
~~~~~~~~~~

:Test ID: Gnocchi_01
:Test Title: Logs - gnocchi api.log reports listening (address and port in gnocchi-api.conf)
:Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

gnocchi api.log reports listening (address and port) as per gnocchi-api.conf
Api and metricd files exist on the controllers

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Confirm the address corresponds to what is defined in the gnocchi-api.conf file

 ::

   cat /var/log/gnocchi/api.log

   [2018-08-13 14:16:14 +0000] [194853] [INFO] Starting gunicorn 19.7.1
   [2018-08-13 14:16:14 +0000] [194853] [INFO] Listening at: http://192.168.204.2:8041 (194853)
   [2018-08-13 14:16:14 +0000] [194853] [INFO] Using worker: sync
   [2018-08-13 14:16:14 +0000] [195045] [INFO] Booting worker with pid: 195045

2. Confirm new gnocchi-api and metricd files exist on the controllers in the following location

 ::

   controller-0:/etc/init.d# ls -l | grep gnocchi
   -rwxrwxr-x. 1 root root ... gnocchi-api
   -rwxrwxr-x. 1 root root ... gnocchi-metricd


3. Confirm the new gnocchi config files and py files are in the /usr/share/gnocchi location

 ::

   controller-X:/usr/share/gnocchi$ ls
   gnocchi-api.conf
   gnocchi-dist.conf
   gnocchi-api.py
   gnocchi-api.pyc
   gnocchi-api.pyo

4. The gnocchi log & config file locations are specified in the /etc/init.d/gnocchi-api file.

 ::

   gnocchi-api.conf (specifies bind address and number of workers)
   CONFIGFILE="/usr/share/gnocchi/gnocchi-api.conf"
   e.g. bind='<ipaddr:port>' e.g. 192.168.204.2:8041
   workers=# e.g. workers=10

5. Confirm log folder/var/log/gnocchi is specified in gnocchi-dist.conf

 ::

   e.g. default folder #log_dir is /var/log/gnocchi

6. Confirm new gnocchi log folder and logs have been created at /var/log/gnocchi/

 ::

   e.g. LOGFILE="/var/log/gnocchi/api.log"

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Address corresponds to what is defined in the gnocchi-api.conf file
2. Files gnocchi-api and metricd should appear under /etc/init.d
3. New gnocchi config files and py files are in place at /usr/share/gnocchi
4. Gnocchi log & config file locations should be specified in the /etc/init.d/gnocchi-api file
5. Folder should be confirmed in gnocchi-dist.conf
6. New gnocchi log folder and logs have been created


~~~~~~~~~~
Gnocchi_02
~~~~~~~~~~

Test ID: 2
Test Title: Gnocchi_resources.yaml and resource metrics changes for 'instance'
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Resources types in Gnocchi are managed by ceilometer

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

+++++++++++
Test Steps:
+++++++++++

1. Check instance resource type still exists but new attribute values have been added (see resource_type: instance)

 ::

	controller-0:/etc/ceilometer# cat gnocchi_resources.yaml | grep  "resource_type: instance"
	  metrics:
		  memory:
		  memory.usage:
		  memory.resident:
		  memory.swap.in:
		  memory.swap.out:
		  memory.bandwidth.total:
		  memory.bandwidth.local:
		 vcpus:   archive_policy_name: ceilometer-low-rate
		 vcpu_util:
		 cpu:     archive_policy_name: ceilometer-low-rate
		  cpu.delta:
		  etc..

2. Checkvcpus and cpu attributes have been added to the instance resource (archive_policy_name 'ceilometer-low-rate')

 ::

   "vcpu_util:" attribute has also been added to the instance resource

3. Check Resource-type, list and show commands

 ::

   openstack metric resource-type list
   openstack metric resource list
   openstack metric resource show

++++++++++++++++++
Expected Behavior:
++++++++++++++++++

1. Display information about resource_type; instance
2. Check vcpus and cpu attributes have been added
3. Every command should display information


~~~~~~~~~~
Gnocchi_03
~~~~~~~~~~

Test ID: 3
Test Title: Gnocchi cli command - get metric list
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Newly created and existing metrics can be listed in different ways
e.g. cli, rest api


++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. On the active controller starting in Release 6, as admin run the following gnocchi command from the cli

 ::

	$gnocchi metric list  (or
	$openstack metric list  (List metrics)

	As of Rel. R6, the metric list returns the following info:
	id  | archive_policy/name | name  | unit | resource_id


	Note: A metric can have the same 'name' but different resources (these are still different metrics)


	Note: Release prior to Rel 6. will refuse the connection
	(gnocchi) metric list
	Unable to establish connection to http://localhost:8041/v1/metric?: HTTPConnectionPool(host='localhost', port=8041): Max retries exceeded with url: /v1/metric (Caused by NewConnectionError('<requests.packages.urllib3.connection.HTTPConnection object at 0x3bdd790>: Failed to establish a new connection: [Errno 111] Connection refused',))


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Verify command displays information


~~~~~~~~~~
Gnocchi_04
~~~~~~~~~~

Test ID: 4
Test Title: Gnocchi cli command - metric show (openstack metric show) - pre and post swact
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Check commands for gnocchi metric show (metric, metric_id and metric_name)

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. On the active controller run:

 ::

	$gnocchi metric show <metric>
	alternative
	$openstack metric show <metric_id>
	$openstack metric show <metric_name> --resource-id <id for the resource>

	The output includes the field and the value

	Note:
	- Each metric is associated with an archive policy
	- the archive policy doesn't change once the metric has been created
	- metrics can have the same name but they are different metrics (different resources can be assigned)



+++++++++++++++++
Expected Behavior
+++++++++++++++++




~~~~~~~~~~
Gnocchi_05
~~~~~~~~~~

Test ID: 5
Test Title: Gnocchi cli command - get gnocchi status (for backlog)
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

status of measurements processing

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. 'metric status' gets the cluster status for metric processing ie, shows the number of metric to process/processing
backlog for gnocchi-metricd (ie. the status of measurements processing)
If the number increases continuously, it could indicate a problem.

 ::

	$gnocchi status
	or
	$openstack metric status
	Field                                               | Value
	storage/number of metric having measures to process
	storage/total number of measures to process



+++++++++++++++++
Expected Behavior
+++++++++++++++++

status of measurements processing is working



~~~~~~~~~~
Gnocchi_06
~~~~~~~~~~

Test ID: 6
Test Title: Attempt list metrics and show measures from standby controller
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Attempt list metrics and show measures from standby controller

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. The openstack metrics commands are rejected on standby controller as authentication is required.
2. The metric command will not work on the standby controller if the passwords is null, invalid ie. should require authentication.
3. The command should work as expected on the standby controller if a valid password is provided (at the Password prompt)

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Openstack metrics commands should be rejected
2. Metric command will not work on the standby controller if the password is null or invalid


~~~~~~~~~~
Gnocchi_07
~~~~~~~~~~

Test ID: 7
Test Title: Metrics for Instance - get metrics for a single instance (capturing vcpu, ram, boot time and cpu related measures)
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Each instance that you launch is a resource in the OpenStack client.
If you want to view a list of resources using the resource show command


++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

The following metrics are associated with instances resources
Check what metrics are associated with the resource

1. List the resources and with the ID execute resource show

 ::

	$ gnocchi resource list | grep 80033029-1e2c-4bac-8843-913a9f7d7e2d
	$gnocchi resource show <resource_id>
	e.g. gnocchi resource show <instance id>

	e.g. The following metrics are captured by default on a single instance


	$ gnocchi resource list | grep <id>
	This lists the resource id, type (e.g. instance) project_id, user_id, original_resource_id, started_at, ended_at, revision_start, revision_end, and creator

	E.g. lists the resources associated with instance_id
	| 80033029-1e2c-4bac-8843-913a9f7d7e2d | instance                   | fb1bdde29a2b4929b505d8a52f5128f4 | 6ac0bb7bcb3a4351a2b6c8b876b62e77 | <instance_id>| 2018-08-10T14:05:32.795230+00:00 | None     | 2018-0     | 6f92553857aa491695c679279af2b1cf:a23d6a91528b4088a09e3e55bbab13e4 |
	| f4292dcb-8896-5f7e-8bb4-0bf55296873b | instance_disk              | fb1bdde29a2b4929b505d8a52f5128f4 | 6ac0bb7bcb3a4351a2b6c8b876b62e77 | <instanceid>-vda | 2018-08-10T14:16:07.614060+00:00 | None     | 2018-0     | 6f92553857aa491695c679279af2b1cf:a23d6a91528b4088a09e3e55bbab13e4 |


	$ gnocchi resource show <instance id> output will include the metrics associated with the resource for that instance
	Field   | Value
	...
	| id                    | 80033029-1e2c-4bac-8843-913a9f7d7e2d                                |
	| metrics               |
	compute.instance.booting.time: 22f5fa88-5045-4c13-a77f-5a48142a2722 |
	cpu.delta: f10ebd09-b67b-4b62-950d-69954ad96bc1                     |
	cpu: 317cd1c1-ded6-4fba-9d20-7ac13df5677e                           |
	cpu_util: 0f0716c7-5ed4-40fc-a91b-05968c2f09ae                      |
	...
	memory: c04e51e7-145d-4f21-ac12-b951636ce627                        |
	vcpu_util: 80c61244-a74a-4852-bded-ae577065af2c                     |
	vcpus: e0d6fb1d-0203-4a9e-8581-02452476034e

	(+ disk related measures:
	disk.allocation: 7a5f4b5a-82db-4cc1-9025-4966b367ad3c               |
	disk.capacity: 7cfb727e-2c35-40db-8099-3bd269393870                 |
	disk.ephemeral.size: 89f7be97-f9c5-4b4e-9931-05097d6731dd           |
	disk.read.bytes.rate: 5cc69603-9c09-4a76-9c32-3e2dd42aaebb          |
	disk.read.bytes: d02e85f5-703d-4fe5-9f9e-bc000b6b8a12               |
	disk.read.requests.rate: 0cffa6c4-abda-49b4-82b7-0920805a7c8b       |
	disk.read.requests: 4f22780a-61d1-4944-a8a8-b3cf23a6f208            |
	disk.root.size: 993072c5-cea7-41ec-9de2-86884a18a4b8                |
	disk.usage: 04a778d7-621d-440f-b282-64dbc00b132d                    |
	disk.write.bytes.rate: 1f3918a7-1bcd-4999-90a7-882a5c8f25ce         |
	disk.write.bytes: e4ecfd47-c4fd-403f-847c-64029ef5a59a              |
	disk.write.requests.rate: 46e1cd6e-38ff-4bba-8ba2-2535734d295e      |
	disk.write.requests: a5cc9622-8fa7-49c6-94df-7206d170f8dd           |)


	original_resource_id  | 80033029-1e2c-4bac-8843-913a9f7d7e2d                                |
	| project_id            | fb1bdde29a2b4929b505d8a52f5128f4



+++++++++++++++++
Expected Behavior
+++++++++++++++++

Check resource list and resource show and which metrics are associated with the resource



~~~~~~~~~~
Gnocchi_08
~~~~~~~~~~

Test ID: 8
Test Title: Metric archive policies - archive policy default, create, list, show, delete in gnocchi
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Archive policies define how the metrics are aggregated and how long they are stored. Each archive policy definition
is expressed as the number of points over a timespan.

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

The default archive policies are listed using the following command

1. List the Archive-Policy

 ::

	# gnocchi archive-policy list
	Or alternatively
	$ openstack metric archive-policy list
	Each archive-policy has a name, definition and aggregation_methods  (and possibly back_window)
	Each definition has points, granularity, and timespan values

2. Show the metrics from archive-policy

 ::

	$ openstack metric archive-policy show
	Field and value are displayed for aggregation_methods, back_window, definition and name

	The names (low, medium, high) describes the storage space and CPU usage needs.
	The bool archive policy only stores one data point for each second with a one year retention period.

3. Create a new archive-policy

 ::

	$ openstack metric archive-policy create

4. Delete the archive-policy

 ::

	$ openstack metric archive-policy delete


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Archive-Policy are listed successfully
2. Metrics from Archive-Policy are shown
3. New Archive-Policy is created
4. Archive-Policy can be deleted



~~~~~~~~~~
Gnocchi_09
~~~~~~~~~~

Test ID: 9
Test Title: Configuration - Default archive policy rules list, create, delete in gnocchi (low, all metrics)
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

The archive policies define how the metrics are aggregated and how long they are stored. Each archive policy definition is expressed as the number of points over a timespan.

The default archive policy rule is “low” for all metrics

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

gnocchi archive-policy-rule list
returns the default archive policy (low)
and default metric pattern *

1. List the Archive-policy-rule to check the rule

 ::

	$ gnocchi archive-policy-rule list

	Or openstack command to list archive policy rules
	$ openstack metric archive-policy-rule list

	+---------+---------------------+----------------+
	| name    | archive_policy_name | metric_pattern |
	+---------+---------------------+----------------+
	| default | low                 | *              |
	+---------+---------------------+----------------+



2. Alternatively execute metric archive-policy-rule list
   List archive policy rules

 ::

	$ openstack metric archive-policy-rule

3. Create an archive policy rule

 ::

    $ metric archive-policy-rule create

4. Delete an archive policy rule

 ::

    $ metric archive-policy-rule delete

5. Show an archive policy rule

 ::

	$ metric archive-policy-rule show

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Rule should appear as Low
2. Archive policy rules listed
3. New Archive-Policy is created
4. Archive-Policy can be deleted
5. Metrics from Archive-Policy are shown


~~~~~~~~~~
Gnocchi_10
~~~~~~~~~~

Test ID: 10
Test Title: Get openstack metric list and measures show on lab configured with https
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Get openstack metric list and measures show on lab configured with https

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Get openstack metric list and measures show on lab configured with https

 ::

	$openstack metric list | grep cpu_util
	$openstack metric list | grep cpu
	$openstack metric list | grep cpu_util

	$ openstack metric measures show <metric _id vcpu_util>
	$ openstack metric measures show <metric _id cpu_util>
	$ openstack metric measures show <metric _id cpu>

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Get metric list and measures

~~~~~~~~~~
Gnocchi_11
~~~~~~~~~~

Test ID: 11
Test Title: Ceilometer no longer in system service-parameter-list or service-parameter-modify operations
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

System command could be used to modify the metering_time_to_live value for service ceilometer

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Prior to release 6, the ceilometer service was listed and the system command could be used to modify the metering_time_to_live value for service ceilometer.

 ::

	e.g.
	$ system service-parameter-list
	<id> | service   | section     | name                     |value
		   ceilometer   database       metering_time_to_live     86400

	As of release 6, the ceilometer service will no longer listed in the service-parameter-list
	The metering_time_to_live value for service ceilometer can no longer be modified.


+++++++++++++++++
Expected Behavior
+++++++++++++++++

Check if Celiometer no loger exist

~~~~~~~~~~
Gnocchi_12
~~~~~~~~~~

Test ID: 12
Test Title: Metrics for compute.node - get metrics for cpu related nova_compute resource
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

OpenStack Compute is capable of collecting CPU related meters from the compute host machines. (compute_monitors option is cpu.virt_driver in the nova.conf configuration file).


++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Confirm /etc/nova.conf has this set compute_monitors=cpu.virt_driver,platform.platform_monitor,vswitch.vswitch_monitor

 ::

   # cat /etc/ceilometer/gnocchi_resources.yaml | grep compute.node  (this is for  resource_type: nova_compute)
	metrics:
		  compute.node.cpu.frequency:
		  compute.node.cpu.idle.percent:
		  compute.node.cpu.idle.time:
		  compute.node.cpu.iowait.percent:
		  compute.node.cpu.iowait.time:
		  compute.node.cpu.kernel.percent:
		  compute.node.cpu.kernel.time:
		  compute.node.cpu.percent:
		  compute.node.cpu.user.percent:
		  compute.node.cpu.user.time:


   # gnocchi resource list | grep nova_compute
   (Or # openstack metric resource list | grep nova_compute)

   # openstack metric list | grep <resource_id>

+++++++++++++++++
Expected Behavior
+++++++++++++++++

Metrics for cpu related to nova_compute should be displayed

~~~~~~~~~~
Gnocchi_13
~~~~~~~~~~

Test ID: 13
Test Title: Gnocchi user listed as protected service in keystone
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Confirm gnocchi user listed as protected service in keystone

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Execute cat /etc/keystone/policy.json

 ::

   cat /etc/keystone/policy.json

   "protected_services": [["'aodh':%(target.user.name)s"],
							   ["'ceilometer':%(target.user.name)s"],
							   ["'cinder':%(target.user.name)s"],
							   ["'glance':%(target.user.name)s"],
							   ["'heat':%(target.user.name)s"],
							   ["'neutron':%(target.user.name)s"],
							   ["'nova':%(target.user.name)s"],
							   ["'patching':%(target.user.name)s"],
							   ["'sysinv':%(target.user.name)s"],
							   ["'mtce':%(target.user.name)s"],
							   ["'magnum':%(target.user.name)s"],
							   ["'murano':%(target.user.name)s"],
							   ["'panko':%(target.user.name)s"],
							   >>["'gnocchi':%(target.user.name)s"]], <<

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Check the list in the file policy.son

 ::

    protected_services

        ["'gnocchi':%(target.user.name)s"]],

~~~~~~~~~~
Gnocchi_14
~~~~~~~~~~

Test ID: 14
Test Title: Logs - gnocchi metric server version in metricd.log, and status on measurements waiting to be processed
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

On the controllers the metricd.log exists in the new gnocchi log folder version of Gnocchi also reported in the metricd.log
The stats on # of measurements and metrics are reported by the log 'metricd.log'.
It will also be reported using the openstack metric status command

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Verify output from /var/log/gnocchi/metricd.log and status

 ::


   cat /var/log/gnocchi/metricd.log

   e.g.

   INFO     gnocchi.service: Gnocchi version 4.2.5

   INFO     gnocchi.cli.metricd: # measurements bundles across # metrics wait to be processed.

   $openstack metric status    (or alternatively $gnochhi status)

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Metricd.log verified with Gnocchi version and status is displayed by metric status


~~~~~~~~~~
Gnocchi_15
~~~~~~~~~~

Test ID: 15
Test Title: Logs - postgres.log and gnocchi events
Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

Should no longer see db=ceilometer in this log in Rel. 6
Should see entries for 'automatic analyze of table "gnocchi..."

++++++++++++++++++++
Test Pre-Conditions:
++++++++++++++++++++

StarlingX environment setup

++++++++++
Test Steps
++++++++++

1. Confirm db is now reported as gnocchi (no longer ceilometer) in postgres.log

 ::

    cat /var/log/postgres.log | grep gnocchi

    Should no longer see db=ceilometer in this log in Rel. 6
    should now have db=gnocchi instead


+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Celiometer should no longer see db=ceilometer in this log

~~~~~~~~~~~
References:
~~~~~~~~~~~

[0] - [https://wiki.openstack.org/wiki/Gnocchi]
[1] - [https://opensource.com/article/17/11/getting-started-gnocchi]
[2] - [https://gnocchi.xyz/stable_3.0/]
[3] - [https://github.com/gnocchixyz/gnocchi]

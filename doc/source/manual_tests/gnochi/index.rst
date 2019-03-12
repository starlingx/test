=======
GNOCCHI
=======

Gnocchi is an open-source time series database, the problem that Gnocchi solves
is the storage and indexing of time series data and resources at a large scale.
This is useful in modern cloud platforms which are not only huge but also are
dynamic and potentially multi-tenant. Gnocchi takes all of that into account.
Gnocchi has been designed to handle large amounts of aggregates being stored
while being performant, scalable and fault-tolerant. While doing this, the goal
was to be sure to not build any hard dependency on any complex storage system.
Gnocchi takes a unique approach to time series storage: rather than storing raw
data points, it aggregates them before storing them. This built-in feature is
different from most other time series databases, which usually support this
mechanism as an option and compute aggregation (average, minimum, etc.) at
query time. Because Gnocchi computes all the aggregations at ingestion getting
the data back is extremely fast, as it just needs to read back the pre-computed
results.


--------------------
Overall Requirements
--------------------

Environemnt setup

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
:Test Title: Logs - gnocchi api.log reports listening (address and port in
             gnocchi-api.conf)
:Tags: Gnocchi

++++++++++++++
Test Objective
++++++++++++++

gnocchi api.log reports listening (address and port) as per gnocchi-api.conf
Api and metricd files exist on the controllers

+++++++++++++++++++
Test Pre-Conditions
+++++++++++++++++++

Environment setup

++++++++++
Test Steps
++++++++++

1. Confirm the address corresponds to what is defined in the gnocchi-api.conf
   file

 ::

   cat /var/log/gnocchi/api.log

   [2018-08-13 14:16:14 +0000] [194853] [INFO] Starting gunicorn 19.7.1
   [2018-08-13 14:16:14 +0000] [194853] [INFO] Listening at: http://192.168.204.2:8041 (194853)
   [2018-08-13 14:16:14 +0000] [194853] [INFO] Using worker: sync
   [2018-08-13 14:16:14 +0000] [195045] [INFO] Booting worker with pid: 195045

2. Confirm new gnocchi-api and metricd files exist on the controllers in the
   following location

 ::

   controller-0:/etc/init.d# ls -l | grep gnocchi
   -rwxrwxr-x. 1 root root ... gnocchi-api
   -rwxrwxr-x. 1 root root ... gnocchi-metricd


3. Confirm the new gnocchi config files and py files are in the
   /usr/share/gnocchi location

 ::

   controller-X:/usr/share/gnocchi$ ls
   gnocchi-api.conf
   gnocchi-dist.conf
   gnocchi-api.py
   gnocchi-api.pyc
   gnocchi-api.pyo

4. The gnocchi log & config file locations are specified in the
   /etc/init.d/gnocchi-api file.

 ::

   gnocchi-api.conf (specifies bind address and number of workers)
   CONFIGFILE="/usr/share/gnocchi/gnocchi-api.conf"
   eg. bind='<ipaddr:port>' eg. 192.168.204.2:8041
   workers=# eg. workers=10

5. Confirm log folder/var/log/gnocchi is specified in gnocchi-dist.conf

 ::

   eg. default folder #log_dir is /var/log/gnocchi

6. Confirm new gnocchi log folder and logs have been created at
   /var/log/gnocchi/

 ::

   eg. LOGFILE="/var/log/gnocchi/api.log"

+++++++++++++++++
Expected Behavior
+++++++++++++++++

1. Address corresponds to what is defined in the gnocchi-api.conf file
2. Files gnocchi-api and metricd should appear under /etc/init.d
3. New gnocchi config files and py files are in place at /usr/share/gnocchi
4. Gnocchi log & config file locations should be specified in the
   /etc/init.d/gnocchi-api file
5. Folder should be confirmed in gnocchi-dist.conf
6. New gnocchi log folder and logs have been created

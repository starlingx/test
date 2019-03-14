=====================
HORIZON Functionality
=====================


.. contents::
   :local:
   :depth: 1

------------------------
HORIZON_functionality_01
------------------------

:Test ID: HORIZON_functionality_01
:Test Title: Image of volume - metadata update.
:Tags: functionality

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Edit Image of volume in Horizon and add Instance Auto Recovery, verify
metadata updated.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

* Getting admin password credentials.

**Note:** Do this from a new shell as a root user (do not source
/etc/platform/openrc in that shell).

**Note:** The 'password' (in below script) should be set to the admin password
which configured during config_controller.

.. code:: bash

  $ mkdir -p /etc/openstack
  $ tee /etc/openstack/clouds.yaml << EOF

  clouds:
    openstack_helm:
      region_name: RegionOne
      identity_api_version: 3
      auth:
      username: 'admin'
      password: '<admin_password>'
      project_name: 'admin'
      project_domain_name: 'default'
      user_domain_name: 'default'
      auth_url: 'http://keystone.openstack.svc.cluster.local/v3'

      EOF

  $ export OS_CLOUD=openstack_helm
  $ openstack endpoint list

**REMARK:** This test case is intended for test Horizon, please create flavor,
image, network, subnetwork, by using the Horizon UI, please take CLI commands
as a reference.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a Flavor.

.. code:: bash

  $ openstack flavor create --public --id 1 --ram 512 --vcpus 1 --disk 4 m1.tiny

2. Create an Image.

.. code:: bash

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

**REMARK:** Make sure in copy cirros... image in your controller-0.

3. Create a Network and Sub network.

.. code:: bash

  $ openstack network create net
  $ openstack subnet create --network net --ip-version 4 --subnet-range 192.168.0.0/24 --dhcp net-subnet1

4. Go to Project -> Compute -> Images, from dropdown menu of Image click on
Create Volume.

5. Go to Project -> Volumes -> Volumes, from dropdown menu Launch an Instance.

6. Go to Project -> Compute -> Instances, from dropdown menu click on Update
Metadata

7. Look for "Instance Auto Recovery", add feature and click on Save.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Flavor created successfully.

2. Image created successfully.

3. Network created successfully.

4. Volume created successfully.

5. Instance created successfully.

6. Metadata updated successfully.

7. Feature updated successfully.

------------------------
HORIZON_functionality_02
------------------------

:Test ID: HORIZON_functionality_02
:Test Title: image of snapshot - metadata update.
:Tags: functionality

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

Edit Image of snapshot in Horizon and add Instance Auto Recovery, verify
metadata updated.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

* Getting admin password credentials.

**Note:** Do this from a new shell as a root user (do not source
/etc/platform/openrc in that shell).

**Note:** The 'password' (in below script) should be set to the admin password
which configured during config_controller.

.. code:: bash

  $ mkdir -p /etc/openstack
  $ tee /etc/openstack/clouds.yaml << EOF

  clouds:
    openstack_helm:
      region_name: RegionOne
      identity_api_version: 3
      auth:
      username: 'admin'
      password: '<admin_password>'
      project_name: 'admin'
      project_domain_name: 'default'
      user_domain_name: 'default'
      auth_url: 'http://keystone.openstack.svc.cluster.local/v3'

      EOF

  $ export OS_CLOUD=openstack_helm
  $ openstack endpoint list

**REMARK:** This test case is intended for test Horizon, please create flavor,
image, network, subnetwork, by using the Horizon UI, please take CLI commands
as a reference.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a Flavor.

.. code:: bash

  $ openstack flavor create --public --id 1 --ram 512 --vcpus 1 --disk 4 m1.tiny

2. Create an Image.

.. code:: bash

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

**REMARK:** Make sure in copy cirros... image in your controller-0.

3. Create a Network and Sub network.


.. code:: bash

  $ openstack network create net
  $ openstack subnet create --network net --ip-version 4 --subnet-range 192.168.0.0/24 --dhcp net-subnet1

4. Go to Project -> Compute -> Images, from dropdown menu of Image click on
Create Volume.

5. Go to Project -> Volumes -> Volumes, from dropdown menu Launch an Instance.

6. Go to Project -> Compute -> Instances, from dropdown menu click on Update
Metadata.

7. Look for "Instance Auto Recovery", add feature and click on Save.

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Flavor created successfully.

2. Image created successfully.

3. Network created successfully.

4. Volume created successfully.

5. Instance created successfully.

6. Metadata updated successfully.

7. Feature updated successfully.

~~~~~~~~~~~
References:
~~~~~~~~~~~

============
HOT Template
============



.. contents::
   :local:
   :depth: 1

--------------------
HEAT_HOT_Template_01
--------------------

:Test ID: HEAT_HOT_Template_01
:Test Title: Heat resource creation for Cinder Volume.
:Tags: HOT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test case verify that HEAT can create a cinder volume successfully with
HOT template.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) An image with the name of cirros available

::

  Export openstack_helm authentication - go to [0] for details.

  $ wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create Heat stack using <cinder_volume.yaml>

::

      $ openstack stack create <Volume_name> -t cinder_volume.yaml

::

  i.e.
  +---------------------+--------------------------------------+
  | Field | Value |
  +---------------------+--------------------------------------+
  | id | caa42023-0669-4825-a024-28ebcbf0e3e2 |
  | stack_name | Volumefer | | description | Launch a cinder volume cirros image. |
  | creation_time | 2019-02-22T15:18:23Z |
  | updated_time | None | | stack_status | CREATE_IN_PROGRESS |
  | stack_status_reason | Stack CREATE started |
  +---------------------+--------------------------------------+

2.Delete the stack

::

      $ openstack stack delete <Volume_name>

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Verify 1GB cinder volume is successfully created.

::

      $ openstack stack show <volume_name>

::

  i.e.
   $ openstack stack show Volumefer
   +------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
   | Field                  | Value                                                                                                                                     |
   +========================+===========================================================================================================================================+
   | id                     | c0a18394-d5fc-441c-bcd9-2f3bb3fb6592                                                                                                      |
   | stack_name             | Volumefer                                                                                                                                 |
   | description            | Launch a cinder volume cirros image.                                                                                                      |
   +------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
   | ...                    | ...                                                                                                                                       |
   +------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
   | outputs                | description: Volume                                                                                                                       |
   | output_key: volume_size|                                                                                                                                           |
   | output_value: '1'      |                                                                                                                                           |
   +------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
   |  ...                    | ...                                                                                                                                       |
   +------------------------+-------------------------------------------------------------------------------------------------------------------------------------------+

2. Verify the STACK and the resources is deleted Openstack stack list (STACK
   should not be there in the list)

~~~~~~~~~~~~~~~~~~~~
<cinder_volume.yaml>
~~~~~~~~~~~~~~~~~~~~

::

 heat_template_version: 2015-10-15
 description: Launch a cinder volume cirros image.
 resources:
   volume:
     type: OS::Cinder::Volume
     properties:
       description: Cinder volume create
       image: cirros
       name: Vol_d
       size: 1

  outputs:
    volume_size:
      description: Volume
      value: { get_attr: [volume, size ] }

--------------------
HEAT_HOT_Template_12
--------------------

:Test ID: HEAT_HOT_Template_12
:Test Title: Heat resource creation for Nova Server.
:Tags: HOT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test case verify that HEAT can create a Nova Server successfully with HOT
template.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) An image with the name of cirros available

::

  i.e.
  Export openstack_helm authentication
     $ export OS_CLOUD=openstack_helm
     REMARK: go to [0] for details.

  $ wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

b) A flavor with the name flavor_name.type available.

::

  i.e.
  $ openstack flavor create --public --id 1 --ram 512 --vcpus 1 --disk 4 flavor_name.type
      REMARK: go to [1] for type of flavors.

c) A network available

::

  i.e.
  $ openstack network create net

  $ openstack subnet create --network net --ip-version 4 --subnet-range 192.168.0.0/24 --dhcp net-subnet1

d) Execute the following command to take the network id

::

  $ export NET_ID=$(openstack network list | awk '/ net / { print $2 }')


~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create Heat stack using nova_server.yaml by typing:

::

      $ openstack stack create --template nova_server.yaml stack_demo --parameter "NetID=$NET_ID"

2. Delete the stack

::

      $ openstack stack delete stack_demo

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Verify Stack is successfully created and new nova instance is created.

::

     $ openstack stack list

::

  i.e.
  +--------------------------------------+------------+----------------------------------+-----------------+----------------------+----------------------+
  | ID | Stack Name | Project | Stack Status | Creation Time | Updated Time                                                                              |
  +======================================+============+==================================+=================+======================+======================+
  |380bb224-4c41-4b25-b4e8-7291bb1f3129 | stack_demo | 3cfea8788a9c4323937e730e1a7cbf18 | CREATE_COMPLETE | 2019-02-22T11:36:17Z | 2019-02-22T11:36:25Z |
  +--------------------------------------+------------+----------------------------------+-----------------+----------------------+----------------------+

2. Verify the STACK and the resources is deleted $ openstack stack list

~~~~~~~~~~~~~~~~~~
<nova_server.yaml>
~~~~~~~~~~~~~~~~~~

::

  heat_template_version: 2015-10-15
  description: Launch a basic instance with CirrOS image using the ``demo1.tiny`` flavor, ``mykey`` key,  and one network.
  parameters:
    NetID:
      type: string
      description: Network ID to use for the instance.

  resources:
    server:
      type: OS::Nova::Server
      properties:
        image: cirros
        flavor: demo1.tiny
        key_name:
        networks:
        - network: { get_param: NetID }

  outputs:
    instance_name:
      description: Name of the instance
      value: { get_attr: [ server, name ] }
    instance_ip:
      description: IP address of the instance.
      value: { get_attr: [ server, first_address ] }

~~~~~~~~~~~
References:
~~~~~~~~~~~
[0] - [https://wiki.openstack.org/wiki/StarlingX/Containers/Installation]

[1] - [https://docs.openstack.org/nova/pike/admin/flavors2.html]

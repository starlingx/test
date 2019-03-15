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

.. code:: bash

  Export openstack_helm authentication - go to [0] for details.

  $ wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create Heat stack using <cinder_volume.yaml>

.. code:: bash

  $ openstack stack create <Volume_name> -t cinder_volume.yaml

.. code:: bash

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

.. code:: bash

  $ openstack stack delete <Volume_name>

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Verify 1GB cinder volume is successfully created.

.. code:: bash

  $ openstack stack show <volume_name>

.. code:: bash

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

~~~~~~~~~~~~~~~~~~
cinder_volume.yaml
~~~~~~~~~~~~~~~~~~

.. code:: yaml

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
HEAT_HOT_template_02
--------------------

:Test ID: HEAT_HOT_Template_02
:Test Title: Heat resource creation for Cinder Volume Attachment.
:Tags: HOT_template

~~~~~~~~~~~~~~
Test Objective
~~~~~~~~~~~~~~

This test case verify that `OS::Cinder::VolumeAttachment` resource for
associate an existing volume to an existing instance.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

a) A Nova Server Instance already created. Check [2] for creation.

b) A volume already created. Check [3] for creation.

c) Create the "cinder_volume_attachment.yaml" yaml file in your
controller.

.. code:: bash

     controller-0:~$ touch cinder_volume_attachment.yaml

d) Export Instance id in your current session.

.. code:: bash

     controller-0:~$ export Instance_ID=$(openstack server list | awk '/stack_demo*/ {print $2}')

e) Export Volume id in your current session.

.. code:: bash

     controller-0:~$ export Volume_ID=$(openstack volume list | awk '/Vol_demo*/ {print $2}')


~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Associate a volume to an instance by typing:

.. code:: bash

     controller-0:~$ openstack stack create -t cinder_volume_attachment.yaml Vol_attach_Instance --parameter "Volume_ID=$Volume_ID;Instance_ID=$Instance_ID"

.. code:: bash

  +---------------------+----------------------------------------------------------+
  | Field               | Value                                                    |
  +---------------------+----------------------------------------------------------+
  | id                  | 45c92f19-b543-4216-bce5-136b140c74e8                     |
  | stack_name          | Vol_attach_Instance                                      |
  | description         | this is a template that attached a volume to an instance |
  | creation_time       | 2019-03-07T16:00:19Z                                     |
  | updated_time        | None                                                     |
  | stack_status        | CREATE_IN_PROGRESS                                       |
  | stack_status_reason | Stack CREATE started                                     |
  +---------------------+----------------------------------------------------------+

2. List your stacks and make sure the volume was associated to the instance.

.. code:: bash

  controller-0:~$ openstack stack list

3. Delete the stack Vol_attach_Instance and make sure the stack and the resources are deleted.

.. code:: bash

  controller-0:~$ openstack stack delete

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Volume was associated to the instance successfully.

2. Vol_attach_Instance listed successfully.

.. code:: bash

  +--------------------------------------+---------------------+----------------------------------+-----------------+----------------------+--------------+
  | ID                                   | Stack Name          | Project                          | Stack Status    | Creation Time        | Updated Time |
  +--------------------------------------+---------------------+----------------------------------+-----------------+----------------------+--------------+
  | 45c92f19-b543-4216-bce5-136b140c74e8 | Vol_attach_Instance | 86ab4e9a23d644d5a378e9b637dc5f5e | CREATE_COMPLETE | 2019-03-07T16:00:19Z | None         |
  | 229be306-6e5d-4b4c-93cc-a22b75f677c9 | Volume_demo_stack   | 86ab4e9a23d644d5a378e9b637dc5f5e | CREATE_COMPLETE | 2019-03-07T15:38:40Z | None         |
  | 1f18959c-2d04-4def-8323-b2497bb3b745 | stack_demo          | 86ab4e9a23d644d5a378e9b637dc5f5e | CREATE_COMPLETE | 2019-03-07T15:27:58Z | None         |
  +--------------------------------------+---------------------+----------------------------------+-----------------+----------------------+--------------+

3. STACK and resources were deleted successfully

.. code:: bash

    controller-0:~$ openstack stack list

~~~~~~~~~
Templates
~~~~~~~~~

~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cinder_volume_attachment.yaml
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

  heat_template_version: 2015-04-30
  description: this is a template that attached a volume to an instance

  parameters:
    Instance_ID:
      type: string
      description: Instance ID to attach to the corresponding volume
    Volume_ID:
      type: string
      description: Volume ID to where the instance is attached

  resources:
    the_resource:
      type: OS::Cinder::VolumeAttachment
      properties:
        instance_uuid:  { get_param: Instance_ID }
        volume_id:  { get_param: Volume_ID }



~~~~~~~~~~~~~~~~~~
cinder_volume.yaml
~~~~~~~~~~~~~~~~~~

.. code:: yaml

  heat_template_version: 2015-10-15
  description: Launch a cinder volume cirros image.

  resources:
    volume:
      type: OS::Cinder::Volume
      properties:
        description: Cinder volume create
        image: cirros
        name: Vol_demo
        size: 1

  outputs:
    volume_size:
      description: Volume
      value: { get_attr: [volume, size ] }

~~~~~~~~~~~~~~~~
nova_server.yaml
~~~~~~~~~~~~~~~~

.. code:: yaml

  heat_template_version: 2015-10-15
  description: Launch a basic instance with CirrOS image using the
               ``demo1.tiny`` flavor, ``mykey`` key,  and one network.

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

--------------------
HEAT_HOT_Template_03
--------------------

:Test ID: HEAT_HOT_Template_03
:Test Title: Heat resource creation for a Neutron network with its Sub-net.
:Tags: HOT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test case verify that HEAT can manage Neutron network with its subnet
successfully using HOT template.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

.. code:: bash

  Export openstack_helm authentication - go to [0] for details.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a network with its subnet using <neutron_subnet.yaml>

.. code:: bash

  $ openstack stack create <net_subnet_name> -t neutron_subnet.yaml

.. code:: bash

  +---------------------+---------------------------------------+
  | Field               | Value                                 |
  +---------------------+---------------------------------------+
  | id                  | 7d9ac4d3-dccc-4856-a056-feb535a9bd0d  |
  | stack_name          | publicnet                             |
  | description         | Manage a Neutron net with its subnet. |
  | creation_time       | 2019-03-15T14:28:32Z                  |
  | updated_time        | None                                  |
  | stack_status        | CREATE_IN_PROGRESS                    |
  | stack_status_reason | Stack CREATE started                  |
  +---------------------+---------------------------------------+

2.Delete the stack

.. code:: bash

  $ openstack stack delete <net_subnet_name>

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Verify networi with its subne is successfully created.

.. code:: bash

  $ openstack stack show <net_subnet_name>

.. code:: bash

  i.e.
  +-----------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                 | Value                                                                                                                                     |
  +-----------------------+-------------------------------------------------------------------------------------------------------------------------------------------+
  | id                    | 0948eb44-9e6a-46a6-bf42-dce80d730f79                                                                                                      |
  | stack_name            | publicnet                                                                                                                                 |
  | description           | Manage a Neutron net with its subnet.                                                                                                     |
  | creation_time         | 2019-03-15T15:32:20Z                                                                                                                      |
  | updated_time          | None                                                                                                                                      |
  | stack_status          | CREATE_COMPLETE                                                                                                                           |
  | stack_status_reason   | Stack CREATE completed successfully                                                                                                       |
  | parameters            | OS::project_id: 983e6f5336ab408589d0d1f424634c51                                                                                          |
  |                       | OS::stack_id: 0948eb44-9e6a-46a6-bf42-dce80d730f79                                                                                        |
  |                       | OS::stack_name: publicnet                                                                                                                 |
  |                       |                                                                                                                                           |
  | outputs               | - description: parent_port_name_output                                                                                                    |
  |                       |   output_key: parent_port_name                                                                                                            |
  |                       |   output_value: parent_port_name                                                                                                          |
  |                       | - description: a_net_name_output                                                                                                          |
  |                       |   output_key: a_net_name                                                                                                                  |
  |                       |   output_value: net_demo                                                                                                                  |
  +-----------------------+-------------------------------------------------------------------------------------------------------------------------------------------+

2. Verify the STACK and the resources is deleted Openstack stack list (STACK
   should not be there in the list)

~~~~~~~~~~~~~~~~~~~
neutron_subnet.yaml
~~~~~~~~~~~~~~~~~~~

.. code:: yaml

  heat_template_version: 2015-04-30

  description: Manage a Neutron net with its subnet.

  resources:
    a_net:
      type: OS::Neutron::Net
      properties:
        name: net_demo
        shared: True

    subnet0:
      type: OS::Neutron::Subnet
      properties:
        network: { get_resource: a_net }
        cidr: 10.0.4.0/24

    parent_port:
      type: OS::Neutron::Port
      properties:
        network: { get_resource: a_net }
        name: parent_port_name

  outputs:
    a_net_name:
      description: a_net_name_output
      value: { get_attr: [ a_net, name ] }
    parent_port_name:
      description: parent_port_name_output
      value: { get_attr: [ parent_port, name ] }

--------------------
HEAT_HOT_Template_04
--------------------

:Test ID: HEAT_HOT_Template_04
:Test Title: Heat resource creation for Neutron Provider Networks.
:Tags: HOT

~~~~~~~~~~~~~~~~~~
Testcase Objective
~~~~~~~~~~~~~~~~~~

This test case verify that HEAT can manage Neutron provider networks
successfully with HOT template.

~~~~~~~~~~~~~~~~~~~
Test Pre-Conditions
~~~~~~~~~~~~~~~~~~~

.. code:: bash

  Export openstack_helm authentication - go to [0] for details.

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create a provider network using <neutron_provider_net.yaml>

.. code:: bash

  $ openstack stack create <provider_net_name> -t neutron_provider_net.yaml

.. code:: bash

  +---------------------+--------------------------------------------+
  | Field               | Value                                      |
  +---------------------+--------------------------------------------+
  | id                  | f2432aca-852a-4d0f-81b0-c466ac86af67       |
  | stack_name          | a_provider                                 |
  | description         | Template to test provide network resources |
  | creation_time       | 2019-03-15T16:05:36Z                       |
  | updated_time        | None                                       |
  | stack_status        | CREATE_IN_PROGRESS                         |
  | stack_status_reason | Stack CREATE started                       |
  +---------------------+--------------------------------------------+


2.Delete the stack

.. code:: bash

  $ openstack stack delete <provider_net_name>

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Verify the provider network is successfully created.

.. code:: bash

  $ openstack stack show <provider_net_name>

.. code:: bash

  i.e.
  controller-0:~$ openstack stack show a_provider
  +-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------+
  | Field                 | Value                                                                                                                                      |
  +-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------+
  | id                    | f2432aca-852a-4d0f-81b0-c466ac86af67                                                                                                       |
  | stack_name            | a_provider                                                                                                                                 |
  | description           | Template to test provide network resources                                                                                                 |
  | creation_time         | 2019-03-15T16:05:36Z                                                                                                                       |
  | updated_time          | None                                                                                                                                       |
  | stack_status          | CREATE_COMPLETE                                                                                                                            |
  | stack_status_reason   | Stack CREATE completed successfully                                                                                                        |
  | parameters            | OS::project_id: 983e6f5336ab408589d0d1f424634c51                                                                                           |
  |                       | OS::stack_id: f2432aca-852a-4d0f-81b0-c466ac86af67                                                                                         |
  |                       | OS::stack_name: a_provider                                                                                                                 |
  |                       |                                                                                                                                            |
  | outputs               | - description: provider_net                                                                                                                |
  |                       |   output_key: net_name                                                                                                                     |
  |                       |   output_value:                                                                                                                            |
  |                       |     admin_state_up: true                                                                                                                   |
  |                       |     availability_zone_hints: []                                                                                                            |
  |                       |     availability_zones: []                                                                                                                 |
  |                       |     created_at: '2019-03-15T16:05:38Z'                                                                                                     |
  |                       |     description: ''                                                                                                                        |
  |                       |     id: aeff6fba-606e-4616-a53f-6fdb111687fb                                                                                               |
  |                       |     ipv4_address_scope: null                                                                                                               |
  |                       |     ipv6_address_scope: null                                                                                                               |
  |                       |     mtu: 1500                                                                                                                              |
  |                       |     name: a_provnet                                                                                                                        |
  |                       |     port_security_enabled: true                                                                                                            |
  |                       |     project_id: 983e6f5336ab408589d0d1f424634c51                                                                                           |
  |                       |     provider:network_type: vlan
  |                       |     provider:physical_network:physnet1
  |                       |     provider:segmentation_id:526
  +-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------+

2. Verify the STACK and the resources is deleted Openstack stack list (STACK
   should not be there in the list)

~~~~~~~~~~~~~~~~~~~~~~~~~
neutron_provider_net.yaml
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

  heat_template_version: 2015-10-15

  description: Template to test provide network resources

  resources:
    a_net:
      type: OS::Neutron::ProviderNet
      properties:
        name: a_provnet
        network_type: vlan
        shared: true

  outputs:
    net_name:
      description: provider_net
      value: { get_attr: [ a_net, show] }

--------------------
HEAT_HOT_Template_11
--------------------

:Test ID: HEAT_HOT_Template_11
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

.. code:: bash

  i.e.
  Export openstack_helm authentication
     $ export OS_CLOUD=openstack_helm
     REMARK: go to [0] for details.

  $ wget http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img

  $ openstack image create --file cirros-0.4.0-x86_64-disk.img --disk-format qcow2 --public cirros

b) A flavor with the name flavor_name.type available.

.. code:: bash

  i.e.
  $ openstack flavor create --public --id 1 --ram 512 --vcpus 1 --disk 4 flavor_name.type
      REMARK: go to [1] for type of flavors.

c) A network available

.. code:: bash

  i.e.
  $ openstack network create net

  $ openstack subnet create --network net --ip-version 4 --subnet-range 192.168.0.0/24 --dhcp net-subnet1

d) Execute the following command to take the network id

.. code:: bash

  $ export NET_ID=$(openstack network list | awk '/ net / { print $2 }')

~~~~~~~~~~
Test Steps
~~~~~~~~~~

1. Create Heat stack using nova_server.yaml by typing:

.. code:: bash

      $ openstack stack create --template nova_server.yaml stack_demo --parameter "NetID=$NET_ID"

2. Delete the stack

.. code:: bash

      $ openstack stack delete stack_demo

~~~~~~~~~~~~~~~~~
Expected Behavior
~~~~~~~~~~~~~~~~~

1. Verify Stack is successfully created and new nova instance is created.

.. code:: bash

       $ openstack stack list

.. code:: bash

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

.. code:: yaml

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

[2] - HEAT_HOT_Template_12 Test Case

[3] - HEAT_HOT_Template_01 Test Case
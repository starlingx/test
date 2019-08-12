.. default-role:: code

=====================================================
StarlingX Test Suite
=====================================================

.. image:: .images/starlingx.png

.. contents:: Table of contents:
   :local:
   :depth: 4


Introduction
============

This Test Suite provides an automated way to Setup, Provision and do a Sanity
Test of the 4 basic StarlingX Deployments options described at
`StarlingX Installation Guide`__. Currently the suite has fully support to
deploy on virtual environments using Libvirt/Qemu to simulate the nodes,
installation on BareMetal is only supported for a very specific infrastructure
that is described on `BareMetal`_, complete documentation for this process will
be ready soon.

Suite is based on Robot Framework and Python, please follow below instructions
to properly use the suite.

***NOTE***:  Currently the suite is designed to run on Pyhton 2.7 environment,
migration to Python 3.5 is undergoing and will be ready soon.

__ https://docs.starlingx.io/deploy_install_guides/index.html

Quick Start
===========
This guide is focused on a clean OS installation, any kind of issue not
document here the user must solve it.

The recommend OS system is **Ubuntu 16.04 LTS**, you can download it from the
following link:

`Download Ubuntu 16.04 LTS`__.

__ http://releases.ubuntu.com/16.04/ubuntu-16.04.5-desktop-amd64.iso

*** Note *** Was also tested on `Debian 9` and `Fedora 27`

Updating the system
--------------------

In order to get the system **up-to-date** you must run the following commands:

.. code:: bash

 $ sudo apt update
 $ sudo apt upgrade

automated-robot-suite repository
--------------------------

Installing Git
``````````````
Before to be able for clone the repository,  a tool is needed and you must
install it typing the following command:

.. code:: bash

 $ sudo apt install git

Cloning the repository
```````````````````````
The next step is to make a copy of this repository in your local machine:

.. code:: bash

 $ git clone https://opendev.org/starlingx/test/src/branch/master/automated-robot-suite

Git configuration
`````````````````
Make sure that you have git correctly configured:

.. code:: bash

 $ git config --global user.name "your name here"
 $ git config --global user.email "your email here"
 $ git config --list

If you have any issues please visit `Troubleshooting`_ section

Host package requirements
-------------------------
Please execute below steps to enable Qemu-Libvirt on your host

1. Add your linux user to **/etc/sudoers** file at the end of the file:

    .. code:: bash

     <your_user> ALL = (root) NOPASSWD:ALL

2. Install the following packages

    .. code:: bash

     $ sudo apt-get install virt-manager libvirt-bin qemu-system

    +--------------+-----------------------------------------------------+
    | Package      | Description                                         |
    +==============+=====================================================+
    | virt-manager | Display the virtual machine desktop management tool |
    +--------------+-----------------------------------------------------+
    | libvirt-bin  | Programs for the libvirt library                    |
    +--------------+-----------------------------------------------------+
    | qemu-system  | QEMU full system emulation binaries                 |
    +--------------+-----------------------------------------------------+

3. Start the libvirt service daemon with the following command:

    .. code:: bash

     $ sudo service libvirt-bin restart

4. Be sure that the daemon is loaded and running

    .. code:: bash

     $ service libvirt-bin status
     ● libvirt-bin.service - Virtualization daemon
        Loaded: loaded (/lib/systemd/system/libvirt-bin.service; enabled; vendor preset: enabled)
        Active: active (running) since Tue 2018-08-21 11:17:36 CDT; 3s ago
          Docs: man:libvirtd(8)
                http://libvirt.org
      Main PID: 5593 (libvirtd)
        CGroup: /system.slice/libvirt-bin.service
                ├─5558 /usr/sbin/dnsmasq --conf-file=/var/lib/libvirt/dnsmasq/default.conf --leasefile-ro --dhcp-script=/usr     /lib/libvirt/libvirt_leaseshelper
                ├─5559 /usr/sbin/dnsmasq --conf-file=/var/lib/libvirt/dnsmasq/default.conf --leasefile-ro --dhcp-script=/usr/lib/libvirt/libvirt_leaseshelper
                ├─5593 /usr/sbin/libvirtd
                └─5630 /usr/sbin/libvirtd

     Aug 21 11:17:36 computing systemd[1]: Starting Virtualization daemon...
     Aug 21 11:17:36 computing systemd[1]: Started Virtualization daemon.

5.  Reboot the system in order that the current user be reflected in
**libvirtd** group, needed to run the services related.

    .. code:: bash

     $ sudo reboot

Project requirements
====================
Every python project has requirement files, in this case the repository
**automated-robot-suite** has the following files:

- **requirements.txt**: which contains all the requirements
  that the project needs.
- **test-requirements.txt**: which contains all the test
  requirements that the project needs.

Python virtual environments
---------------------------
Python “Virtual Environments” allow Python packages to be installed in an
isolated location for a particular application, rather than being installed
globally.

Installation on Virtual Environment
```````````````````````````````````
Make sure you have python **virtualenv** package installed in your host machine.

.. code:: bash

 $ sudo apt install python-pip
 $ sudo pip install virtualenv

You can manage your virtual environments for the two options explained below:

Managing virtual environments with virtualenvwrapper
````````````````````````````````````````````````````
While virtual environments certainly solve some big problems with package
management, they’re not perfect. After creating a few environments, you will
start to see that they create some problems of their own, most of which revolve
around managing the environments themselves. To help with this, the
virtualenvwrapper tool was created, which is just some wrapper scripts around
the main virtualenv tool
A few of the more useful features of virtualenvwrapper are that it:

Organizes all of your virtual environments in one location
Provides methods to help you easily create, delete, and copy environments
Provides a single command to switch between environments

To get started, you can download the wrapper with pip

.. code:: bash

 $ sudo pip install virtualenvwrapper

Once installed, you will need to activate its shell functions, which can be
done by running source on the installed virtualenvwrapper.sh script

.. code:: bash

 $ which virtualenvwrapper.sh
 /usr/local/bin/virtualenvwrapper.sh

Using that path, add the following lines to your shell’s startup file
which is your **~/.bashrc**

.. code:: bash

 export WORKON_HOME=$HOME/.virtualenvs
 export PROJECT_HOME=$HOME/projects
 export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python
 export VIRTUALENVWRAPPER_VIRTUALENV=/usr/local/bin/virtualenv
 export VIRTUALENVWRAPPER_VIRTUALENV_ARGS='--no-site-packages'
 source /usr/local/bin/virtualenvwrapper.sh

Finally, reload your **bashrc** file

.. code:: bash

 $ source ~/.bashrc

For help and examples on Virtualenvwrapper please visit `Help`_ section

Managing virtual environments raw
`````````````````````````````````
If you want a more direct way to work with virtual environment on python
you can follow below steps:

.. code:: bash

 $ virtualenv my-venv
 $ source my-venv/bin/activate

Install the project requirements on virtual environment.
````````````````````````````````````````````````````````
Now that virtualenv is activated you need to install the needed packages.

.. code:: bash

 $ cd <automated-robot-suite>
 $ pip install -r requirements.txt
 $ pip install -r test-requirements.txt

PYTHONPATH
==========
Augment the default search path for module files. The format is the same as
the shell’s PATH: one or more directory pathnames separated by os.pathsep
(e.g: colons on Unix or semicolons on Windows). Non-existent directories are
silently ignored.
In addition to normal directories, individual **PYTHONPATH** entries may refer
to zip files containing pure Python modules (in either source or compiled
form). Extension modules cannot be imported from zip files.
The default search path is installation dependent, but generally begins with
**/prefix/lib/pythonversion**. It is always appended to **PYTHONPATH**.

Setup PYTHONPATH
----------------
**PYTHONPATH** environment variable is a pre requisite for this project.
Please setup **PYTHONPATH** in your local bashrc like below:[#]_

.. code:: bash

 $ export PYTHONPATH="${PYTHONPATH}:../automated-robot-suite"


.. [#]  where **../** indicates the absolute path to the project.


Using the suite
===============
This section will describe how to configure, interact and run test
on the suite based on robot framework, this suite supports two diferent
environments `Virtual`_ and `BareMetal`_

__ https://docs.starlingx.io/deploy_install_guides/upcoming/installation_libvirt_qemu.html

Virtual
-------
Virtual deployment is based on **qemu/libvirt** to create virtual
machines that will host the **StarlingX** deployment

**NOTE** There are minimum HW requirements to deploy on virtual environments please
refer to `installation_libvirt_qemu`__ for more details

Download Artifacts
``````````````````
Suite needs an **ISO** to be installed and the associated **Helm Chart** to
deploy OpenStack services sot they should be downloaded and put inside of
**automated-robot-suite/** path.

There is daily build under **CENGEN** infrastructure so there above items can
be downloaded form there from:

`StarlingX Mirror`__

**ISO** = /*<release>*/outputs/iso/bootimage.iso

**HELM_CHART** = /*<release>*/outputs/helm-charts/stx-openstack-*<VERSION>*-centos-stable-versioned.tgz

__ http://mirror.starlingx.cengn.ca/mirror/starlingx/master/centos/

Suite Configuration
```````````````````
- **config.ini**: This file contains information that will use directly
  by the suite to Setup a deployment, parameters that should be updated are:

   1. **STX_ISO_FILE**: The name of the ISO, for automation purposes
      recommended to let **bootimage.iso** and create a symlink to the
      required ISO.

      .. code:: bash

       ln -sfn stx-2018-10-19-29-r-2018.10.iso bootimage.iso

   2. **CHART_MANIFEST**: With the name of the Helm chart associated to the
      ISO, as well is recommended to have a symlink

   3. **STX_DEPLOY_USER_NAME**: The user name to be setup on the deployment.

   4. **STX_DEPLOY_USER_PSWD**: The password to be setup on the deployment.

- **stx-<configuration>.yml**: Is the configuration file used to configure
  the StarlingX deployment. There is file for **Simplex**, **Duplex** and
  **Multinode** configurations. The structure of this file is out of the scope
  of this document please refer to the official `StarlingX documentation`__
  for more information

__ https://docs.starlingx.io/

- **VM's Resources Yaml**: Definition of the resources that will be used by
  libvirt to create the VM's. those files are stored at **Qemu/configs** and
  are set with the minimum resources needed hence values only can be increased
  according to the host resources.

Suite Execution
```````````````````
The suite is divides in 3 main stages that will be explained below:

Setup
.....
In this stage all the virtual machines are created for the specific
configuration selected and with the attributes previously defined, the ISO
will be installed on the master controller and be configured to be a SatrlingX
deployment.

.. code:: bash

 $python  runner.py --run-suite Setup --configuration <config_number> --environment virtual

Provisioning
............
In this stage all other nodes are installed and system is provisioned following
the steps defined at `StarlingX Installation Guides`__

__ https://docs.starlingx.io/deploy_install_guides/

.. code:: bash

 $python  runner.py --run-suite Provision

Test Execution
..............
In this stage the system is already provisioning and Test can be executed,
below are the steps to execute a **Sanity-Test** suite

1. Download required images

 External: - `Cirros`__  - `Ubuntu`__  - `Centos`__  - `Windows`__

__ http://download.cirros-cloud.net/0.4.0/cirros-0.4.0-x86_64-disk.img
__ http://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img
__ http://cloud.centos.org/centos/7/images/CentOS-7-x86_64-GenericCloud.qcow2
__ https://cloudbase.it/windows-cloud-images/

2. Update **config.ini** with the name of the downloaded images.

   .. code:: bash

    [general]
    CIRROS_FILE = cirros-0.4.0-x86_64-disk.qcow2
    CENTOS_FILE = CentOS-7-x86_64-GenericCloud.qcow2
    UBUNTU_FILE = xenial-server-cloudimg-amd64-disk1.qcow2
    WINDOWS_FILE = windows_server_2012_r2.qcow2

3. Run Tests

   .. code:: bash

    $python runner.py --run-suite Sanity-Test


BareMetal
---------
**Infrastructure Diagram**

.. image:: .images/bm_diagram.png

**PXE client** - This is the main StarlingX controller (controller-0).

**PXE Server** - StarlingX test suite must be executed on this host. Also,
these services are running:

  - *TFTP* - Used to serve uefi/shim.efi file. Indicating where the pxe client
    is going to connect to download installation packages.
  - *HTTP* - Serving the full content of an ISO to the pxe client.
  - *DHCP* - This service assigns a temporal IP address to the pxe client, it
    also tells the clients where to grab the boot shim file.

These services should be running through OAM network. You need to ensure that
TFTP and DHCP are configured properly to serve the shim file. Also, the test
suite needs to identify the temporal IP address that the pxe client is going to
use.

The following is an example of a DHCP configuration file to assing temporal
IP 192.168.150.10 to a pxe client:

::

   host standard_example {
   hardware ethernet aa:bb:cc:dd:ee:ff;
   fixed-address 192.168.150.10;
   }

Also, you need to have this option on the same dhcp configuration file:

::

   filename "uefi/shim.efi";

Test suite will do the following steps to start an install:

1) Mount bootimage.iso and expose it with HTTP
2) Take info from the mounted files to create a custom shim file. This file will
   automatically setup the required boot options for the pxe client.
3) It will use BMC network to send a signal to the pxe client, telling it to
   boot on the first network adapter (pxe boot).
4) Open a SOL connection to the host to monitor the progress of the install,
   once completed, it will change sysadmin password to the one defined on the
   .yml file
5) Copy required rpms to install secondary nodes. This is done using scp from
   the pxe server to the pxe client using the temporal IP address

Results and Logs
----------------
Every execution on the suite generate a separate directory with logs, this is
placed under **Results/** and also a a link to the mos recent execution can be
acceded by **latest-results/** symlink, the list of the available logs is:

 -  **debug.log**: Showing the output form Robot Framework activity.
 -  **iso_setup_console.txt** : Showing the serial output of the ISO
    installation and Configuration on virtual environments.
 -  **iso_setup.error.log**: Filtering only the errors on the serial console.
 -  **qemu_setup.error.log**: Showing the information related to
    *Qemu* and *Libvirt*
 -  **log.html**: Showing the *debug.log* in *HTML* format
 -  **output.xml**: Showing the *debug.log* in *XML* format
 -  **report.html**: Showing the results on a visual and customizable format.

Troubleshooting
===============

GIT
-----------------
- TLS connection was non-properly terminated

  Sometimes trying to clone the repository you could have the following error:

  .. code:: bash

   <git_url>: (35) gnutls_handshake() failed: The TLS connection was non-properly terminated.

  This error message means that git is having trouble setting up such a secure
  connection, to solve this please follow the next steps:

  .. code:: bash

   unset https_proxy
   export http_proxy=http://<PROXY>:<PORT>


PIP
---

- AttributeError: 'module' object has no attribute 'SSL_ST_INIT'

  This error is because the python module that comes with the distribution is
  incompatible with pip version. Please do the following steps to fix it:

  .. code:: bash

   $ sudo apt-get --auto-remove --yes remove python-openssl
   $ pip install pyOpenSSL

- SSL: CERTIFICATE_VERIFY_FAILED

  This is a common issue and this mean that your system date is out-to-date.
  To fix this please setup the correct date in your system.

Suite
-----

- Nodes not being installed

  In some cases was seen that during virtual deployment of Duplex or
  Multi-node the extra nodes (controller-1, computes and storage) are not
  being installed and keeps waiting for PXE image until timeout expires, we
  found that for those cases the guilty of causing controllers not booting
  for pxe is **docker**, for some reason (not yet discovered why) docker
  is sending packages to the interfaces used by the VMs to be installed by PXE
  and this causes unknown traffic on the interface making PXE installation
  fail. The workaround  for now is to kill docker daemon to avoid this issues.

  .. code:: bash

   $sudo status docker
   $sudo stop docker

Help
====
This section will show different topics that could help on  he suite usage.

Increase resources on virtual environment
------------------------------------------
Suite has set the minimum requirements on the virtual machines to support a
**StarlingX** deployment, but is also possible to increase those values if
the host machine has enough resources, follow below steps to increase resources

1. Go to **Qemu/configs/** and open *yaml* file of your configuration

2. Edit file with the values for:

 - partition_a (in GB)
 - partition_b (in GB)
 - partition_d (in GB)
 - memory_size (in MB)
 - system_cores

3. Vales can be increased on **Controllers**, **Computes** and **Storage**
   nodes

Using proxies to download docker images
---------------------------------------
With the support of containers on *StarlingX* deployment there is a need of
downloading docker images, if you are using a proxy please follow below steps
to successfully configure your deployment.

1. Open your configuration file at **Config/stx-<config>.ini** and add below
   section

   .. code:: bash

    [DNS]
    NAMESERVER_1= <IP OF YOUR DNS SERVER>

    [DOCKER_PROXY]
    DOCKER_HTTP_PROXY=<YOUR HTTP PROXY>
    DOCKER_HTTPS_PROXY=<YOUR HTTPS PROXY>
    DOCKER_NO_PROXY=localhost,127.0.0.1,192.168.204.2,192.168.204.3,192.168.204.4,<IPs of the OAM network of all your nodes>

2. Save the file and run **Setup** to have a StarlingX deployment configured
   with docker proxies.

Using local registry to download docker images
----------------------------------------------
With the support of containers on *StarlingX* deployment there is a need of
downloading docker images, if you don't have access to public repositories you
can point docker to sue local registry (how to setup a local registry is out
of the scope of this document), follow below steps:

1. Open your configuration file at **Config/stx-<config>.ini** and delete
   **[DNS]** and **[DOCKER_PROXY]** if exists

2. add below section

   .. code:: bash

    [DOCKER_REGISTRY]
    DOCKER_K8S_REGISTRY=<REGISTRY IP>
    DOCKER_GCR_REGISTRY=<REGISTRY IP>
    DOCKER_QUAY_REGISTRY=<REGISTRY IP>
    DOCKER_DOCKER_REGISTRY=<REGISTRY IP>
    IS_SECURE_REGISTRY=False

Virtualenvwrapper useful commands
---------------------------------

+----------------+---------------------------------------------+
| cmd            | Description                                 |
+================+=============================================+
| workon         | List or change working virtual environments |
+----------------+---------------------------------------------+
| deactivate     | Programs for the libvirt library            |
+----------------+---------------------------------------------+
| rmvirtualenv   | Remove an environment                       |
+----------------+---------------------------------------------+
| mkvirtualenv   | QEMU full system emulation binaries         |
+----------------+---------------------------------------------+
| lsvirtualenv   | List all of the environments                |
+----------------+---------------------------------------------+
| lssitepackages | Shows contents of site-packages directory   |
+----------------+---------------------------------------------+

Virtualenvwrapper Exampes
-------------------------
- Create a virtual environment: This will create and activate a new
  environment in the directory located at $WORKON_HOME, where all
  virtualenvwrapper environments are stored.

  .. code:: bash

   $ mkvirtualenv my-new-virtualenvironment
   (my-new-virtualenvironment) $

- Stop a existing virtual environment: To stop using that environment,
  you just need to deactivate it like before

  .. code:: bash

   (my-new-virtualenvironment) $ deactivate
   $

- List virtual environments: If you have many environments to choose from,
  you can list them all with the workon function

  .. code:: bash

   $ workon
   my-new-virtualenvironment
   my-django-project
   web-scraper

- Activate a existing virtual environment

  .. code:: bash

   $ workon web-scraper
   (web-scraper) $

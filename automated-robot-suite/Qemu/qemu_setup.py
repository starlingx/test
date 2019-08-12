#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""This module setup the controller(s)/computes(s) in the current host"""

from __future__ import print_function

import argparse
from argparse import RawDescriptionHelpFormatter
from imp import reload
import multiprocessing
import os
import re
from shutil import copy
from shutil import rmtree
import sys

# this needs to be exactly here after call network.delete_network_interfaces()
# otherwise the suite local modules they will not be recognized
# hence adding `noqa` to avoid linter issues.
SUITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(SUITE_DIR)

from Config import config  # noqa: E402
from Utils import bash_utils as bash  # noqa: E402
from Utils import logger  # noqa: E402
from Utils import network  # noqa: E402
from Utils import utils  # noqa: E402
import kmodpy  # noqa: E402
import yaml  # noqa: E402

# reloading config.ini
reload(config)

# Global variables
THIS_PATH = os.path.dirname(os.path.abspath(__file__))

# setup the logger
LOG_FILENAME = 'qemu_setup.log'
LOG_PATH = config.get('general', 'LOG_PATH')
LOG = logger.setup_logging(
    'qemu_setup', log_file='{path}/{filename}'.format(
        path=LOG_PATH, filename=LOG_FILENAME), console_log=False)


def enable_nat_network():
    """Enable NAT network for VMs

    This function creates a NAT network to allow VM external connection
    needed for download docker images.

    """

    nat_xml = os.path.join(THIS_PATH, 'nat-network.xml')
    nat_net_name = 'stx-nat'
    bash.run_command('sudo virsh net-define {}'.format(nat_xml))
    bash.run_command('sudo virsh net-start {}'.format(nat_net_name))


def exit_dict_status(code):
    """Exit status

    The aim of this function is to provide a exit status in dictionary format
    as an string in order to grab it for robot for perform actions.

    :param code: which is the exit status code
        code 0: which represents an exit status god.
        code 1: which represents an exit status bad.
    """
    # defining the dictionary

    if code == 1:
        LOG.info('status: FAIL')
    elif code == 0:
        LOG.info('status: PASS')
    else:
        LOG.error('exit code not valid')

    sys.exit(code)


def check_kernel_virtualization():
    """Check kernel virtualization

    Checks if Virtualization Technology is enabled in the BIOS and it is
    present in the kernel as a module.
    QEMU requires KVM (Kernel Virtualization Module) to run the nodes.
    """
    _km = kmodpy.Kmod()
    module_list = [m for m in _km.list()]

    virtualization = filter(lambda mod: mod[0] == 'kvm_intel', module_list)

    if not virtualization:
        message = ('KVM (vmx) is disabled by your BIOS\nEnter your BIOS setup '
                   'and enable Virtualization Technology (VT), and then hard '
                   'power off/power on your system')
        raise OSError(message)


def check_preconditions():
    """Check host preconditions

    The aim of this function is to check the requirements to run QEMU in the
    host.
    """
    # if this script is running through ssh connection the following
    # environment variable needs to be setup in the host bashrc
    if 'DISPLAY' not in os.environ:
        LOG.info('configuring DISPLAY environment variable')
        os.environ['DISPLAY'] = ':0'


def get_system_memory(configurations):
    """Get the system memory

    The aim of this function is to get the system memory to be setup with QEMU.

    :param: configurations
        - which is an object with the values loaded from the yaml.
    :return:
        - system_free_memory: which is the total system free memory.
        - recommended_system_free_memory: which is the recommended system free
            memory.
    """

    # calculating the system memory to be assigned (value in megabytes)
    # os_system_memory will return 0 if either key1 or key2 does not exists
    os_system_memory = configurations.get(
        'general_system_configurations', 0).get("os_system_memory", 0)
    system_free_memory = map(
        int, os.popen('free -m | grep Mem').readlines()[-1][4:].split())[-1]
    # subtracting OS system memory
    recommended_system_free_memory = system_free_memory - os_system_memory

    return system_free_memory, recommended_system_free_memory


def get_free_disk_space(configurations):
    """Get the system free disk space

    The aim of this function if to get the system free disk in order to setup
    with QEMU.

    :param: configurations
        - which is an object with the values loaded from the yaml.
    :return
        - system_free_disk_size: which is the total system free disk size in GB
        - r_system_free_disk_size: which is the recommended system
            free disk size in GB subtracting the disk_space_allocated_to_os
            from yaml configuration file for the host OS in order to avoid
            low performance.
    """
    # disk_space_allocated_to_os will return 0 if either key1 or key2 does
    # not exists
    disk_space_allocated_to_os = configurations.get(
        'general_system_configurations', 0).get(
            "disk_space_allocated_to_os", 0)
    # the mount point in which will be calculated the free space in disk
    default_mount_point = configurations.get(
        'general_system_configurations', 0).get(
            "default_mount_point", '/')
    statvfs = os.statvfs(default_mount_point)
    # the following value will be get in megabytes
    system_free_disk_size = statvfs.f_frsize * statvfs.f_bavail / 1000000000
    # subtracting the 20% of the total disk free
    r_system_free_disk_size = (
        (100 - disk_space_allocated_to_os) * system_free_disk_size / 100)

    return system_free_disk_size, r_system_free_disk_size


def get_system_resources(configurations):
    """Get resources from the current host

    The aim of this function is to get resources for the virtual environment
    with QEMU in order to setup properly it and avoid configuration issues.

    :param: configurations
        - which is an object with the values loaded from the yaml.
    :return:
        - recommended_system_free_memory: which is the recommended system free
            memory to be setup with QEMU.
        - system_free_disk_size: which is the total system free disk size.
        - r_system_free_disk_size: which is the recommended  system
        - r_system_free_disk_size: which is the recommended  system
            free disk size.
        - recommended_system_cores: which is the recommended system cores to be
        setup with QEMU.
    """
    # os_system_cores will return 0 if either key1 or key2 does not exists
    os_system_cores = configurations.get(
        'general_system_configurations', 0).get("os_system_cores", 0)

    # Getting the system free memory and the recommended system memory
    _, recommended_system_free_memory = get_system_memory(
        configurations)

    # Getting the system free disk size and the recommended system free (GB)
    system_free_disk_size, r_system_free_disk_size = (
        get_free_disk_space(configurations))

    # Calculating the system cores to be assigned to the controller/computes
    recommended_system_cores = multiprocessing.cpu_count() - os_system_cores

    return (
        recommended_system_free_memory,
        system_free_disk_size, r_system_free_disk_size,
        recommended_system_cores)


def check_system_resources(configurations):
    """Check basic configurations.

    The aim of this function is to check the following aspects before to
    proceed to configure the nodes.
    - checks if the disk setup by the user in the yaml is less than the
        recommended free space
    - checks if the memory size setup by the user in the yaml is less than the
        recommended memory size.
    - checks if the system cores setup by the user in the yaml is less than the
        recommended system cores.

    :param configurations: which is the object that contains all the
        configurations from the yaml file.
    """
    # checking how many configurations the yaml file has
    configurations_keys = configurations.keys()
    regex = re.compile('configuration_.')
    total_configurations = list(filter(regex.match, configurations_keys))

    # getting the system recommendations
    (recommended_system_free_memory, _,
     r_system_free_disk_size,
     recommended_system_cores) = get_system_resources(configurations)

    # iterating over the total configurations setup in yaml file in order to
    # get the disk/memory space assigned by the user
    user_memory_defined, user_disk_space_defined, user_system_cores_defined = (
        0, 0, 0)

    for configuration in range(0, len(total_configurations)):
        # iterating over the configurations

        current_controller = 'controller-{}'.format(configuration)
        # controller will return NoneType if either key1 or key2 does
        # not exists
        controller = configurations.get(
            'configuration_{}'.format(configuration), {}).get(
                'controller-{}'.format(configuration), {})
        controller_partition_a = int(controller.get(
            'controller_{}_partition_a'.format(configuration)))
        controller_partition_b = int(controller.get(
            'controller_{}_partition_b'.format(configuration)))
        controller_partition_d = int(controller.get(
            'controller_{}_partition_d'.format(configuration)))
        controller_memory = int(controller.get(
            'controller_{}_memory_size'.format(configuration)))
        controller_system_cores = int(controller.get(
            'controller_{}_system_cores'.format(configuration)))

        # checking if the current controller at least has 1 cpu assigned in
        # order to avoid the following error:
        # error: XML error: Invalid CPU topology
        if controller_system_cores < 1:
            LOG.error('{}: must have assigned at least 1 core'.format(
                current_controller))
            exit_dict_status(1)

        # checking how many computes the current controller has
        compute_keys = configurations.get('configuration_{}'.format(
            configuration), {}).keys()
        regex = re.compile('controller-{0}-compute-.'.format(configuration))
        total_computes = list(filter(regex.match, compute_keys))

        for compute_number in range(0, len(total_computes)):
            current_compute = '{0}-compute-{1}'.format(
                current_controller, compute_number)
            # compute will return NoneType if either key1 or key2 does
            # not exists  controller_1_compute_2:
            compute = configurations.get('configuration_{}'.format(
                configuration), {}).get(
                    'controller-{0}-compute-{1}'.format(
                        configuration, compute_number), {})
            compute_partition_a = int(compute.get(
                'controller_{0}_compute_{1}_partition_a'.format(
                    configuration, compute_number)))
            compute_partition_b = int(compute.get(
                'controller_{0}_compute_{1}_partition_b'.format(
                    configuration, compute_number)))
            compute_memory = int(compute.get(
                'controller_{0}_compute_{1}_memory_size'.format(
                    configuration, compute_number)))
            compute_system_cores = int(compute.get(
                'controller_{0}_compute_{1}_system_cores'.format(
                    configuration, compute_number)))

            # checking if the current compute at least has 1 cpu assigned in
            # order to avoid the following error:
            # error: XML error: Invalid CPU topology
            if compute_system_cores < 1:
                LOG.error('{}: must have assigned at least 1 core'.format(
                    current_compute))
                exit_dict_status(1)

            # increasing the variables (computes loop)
            user_disk_space_defined = (
                user_disk_space_defined + compute_partition_a +
                compute_partition_b)
            user_memory_defined = user_memory_defined + compute_memory
            user_system_cores_defined = (
                user_system_cores_defined + compute_system_cores)

        # increasing the variables (controller loop)
        user_disk_space_defined = (
            user_disk_space_defined + controller_partition_a +
            controller_partition_b + controller_partition_d)
        user_memory_defined = user_memory_defined + controller_memory
        user_system_cores_defined = (
            user_system_cores_defined + controller_system_cores)

    # checking the conditions defined in the yaml
    if user_memory_defined > recommended_system_free_memory:
        LOG.error(
            'the memory defined in the yaml is greater than the recommended '
            'free memory')
        LOG.error('user memory defined            : {}'.format(
            user_memory_defined))
        LOG.error('recommended system free memory : {}'.format(
            recommended_system_free_memory))
        exit_dict_status(1)
    elif user_disk_space_defined > r_system_free_disk_size:
        LOG.error(
            'the disk space defined in the yaml is greater than the '
            'recommended free disk size')
        LOG.error('user disk space defined            : {}'.format(
            user_disk_space_defined))
        LOG.error('recommended system free disk size  : {}'.format(
            r_system_free_disk_size))
        exit_dict_status(1)
    elif user_system_cores_defined > recommended_system_cores:
        LOG.error(
            'the system cores defined in the yaml is greater than the '
            'recommended system cores')
        LOG.error('user system cores defined  : {}'.format(
            user_system_cores_defined))
        LOG.error('recommended  system cores  : {}'.format(
            recommended_system_cores))
        exit_dict_status(1)


def setup_controller_computes(iso_file, configurations):
    """Setup the configurations in the host

    This function setup the network and the configurations from yaml in the
    current host.

    :param iso_file: which is the absolute/relative path to the iso file which
    will be setup in the controller(s) node(s).
    :param configurations: which is the object that has all the configurations
        to be setup in the system.
    """
    # define the module's variables
    libvirt_images_path = '/var/lib/libvirt/images'

    # ----------------------------------
    # customize Qemu configuration files
    # ----------------------------------
    utils.qemu_configuration_files()

    # ----------------------------------
    # configuring the network interfaces
    # ----------------------------------
    network.delete_network_interfaces()
    enable_nat_network()
    network.configure_network_interfaces()

    # ------------------------------
    # clean qemu/libvirt environment
    # ------------------------------
    utils.clean_qemu_environment()

    if os.path.exists(os.path.join(THIS_PATH, 'vms')):
        rmtree(os.path.join(THIS_PATH, 'vms'))

    os.mkdir(os.path.join(THIS_PATH, 'vms'))

    # ----------------------------------------------------------
    # iterating over the total configurations setup in yaml file
    # ----------------------------------------------------------

    for controller, values in configurations.get('Controllers').items():
        # iterating over the controllers
        controller_partition_a = int(values.get('partition_a'))
        controller_partition_b = int(values.get('partition_b'))
        controller_partition_d = int(values.get('partition_d'))
        controller_memory = int(values.get('memory_size'))
        controller_system_cores = int(values.get('system_cores'))

        # creating controller's partitions in the system
        bash.run_command(
            'sudo qemu-img create -f qcow2 {0}/{1}-0.img {2}G'.format(
                libvirt_images_path, controller, controller_partition_a),
            raise_exception=True)
        bash.run_command(
            'sudo qemu-img create -f qcow2 {0}/{1}-1.img {2}G'.format(
                libvirt_images_path, controller, controller_partition_b),
            raise_exception=True)
        bash.run_command(
            'sudo qemu-img create -f qcow2 {0}/{1}-2.img {2}G'.format(
                libvirt_images_path, controller, controller_partition_d),
            raise_exception=True)

        # Only controller-0 needs to have the ISO file in order to boot the
        # subsequent controllers
        # heck_controller = False if configuration == 'controller-0' else True

        if controller == 'controller-0':
            bash.run_command(
                'sed -e "s,NAME,{0}," '
                '-e "s,ISO,{1}," '
                '-e "s,UNIT,MiB," '
                '-e "s,MEMORY,{2}," '
                '-e "s,CORES,{3}," '
                '-e "s,DISK0,{4}/{0}-0.img," '
                '-e "s,DISK1,{4}/{0}-1.img," '
                '-e "s,DISK2,{4}/{0}-2.img," '
                '-e "s,destroy,restart," {5}/master_controller.xml > '
                '{5}/vms/{0}.xml'.format(
                    controller, iso_file, controller_memory,
                    controller_system_cores, libvirt_images_path, THIS_PATH),
                raise_exception=True)
        else:
            # this mean that is the controller-N
            # modifying xml parameters for the current controller
            bash.run_command(
                'sed -e "s,NAME,{0}," '
                '-e "s,UNIT,MiB," '
                '-e "s,MEMORY,{1}," '
                '-e "s,CORES,{2}," '
                '-e "s,DISK0,{3}/{0}-0.img," '
                '-e "s,DISK1,{3}/{0}-1.img," '
                '-e "s,DISK2,{3}/{0}-2.img," '
                '-e "s,destroy,restart," {4}/slave_controller.xml > '
                '{4}/vms/{0}.xml'.format(
                    controller, controller_memory,
                    controller_system_cores, libvirt_images_path, THIS_PATH),
                raise_exception=True)

        # the following command define a domain and it does not start it and
        # makes it persistent even after shutdown
        bash.run_command('sudo virsh define {0}/vms/{1}.xml'.format(
            THIS_PATH, controller))

        # starting only the controller-0 which is the one with ISO in the xml
        if controller == 'controller-0':
            # the following command start a domain
            bash.run_command('sudo virsh start {}'.format(
                controller), raise_exception=True)

    if 'Computes' in configurations:
        for compute, values in configurations.get('Computes').items():
            # iterating over the computes
            compute_partition_a = int(values.get('partition_a'))
            compute_partition_b = int(values.get('partition_b'))
            compute_memory = int(values.get('memory_size'))
            compute_system_cores = int(values.get('system_cores'))

            # copy the compute.xml to vms folder
            origin = os.path.join(THIS_PATH, 'compute.xml')
            destination = os.path.join(THIS_PATH,
                'vms', '{}.xml'.format(compute))

            copy(origin, destination)

            # creating both compute's partitions in the system
            bash.run_command(
                'sudo qemu-img create -f qcow2 {0}/{1}-0.img {2}G'.format(
                    libvirt_images_path, compute, compute_partition_a),
                raise_exception=True)
            bash.run_command(
                'sudo qemu-img create -f qcow2 {0}/{1}-1.img {2}G'.format(
                    libvirt_images_path, compute, compute_partition_b),
                raise_exception=True)

            # modifying xml compute parameters
            bash.run_command(
                'sed -i -e "s,NAME,{0}," '
                '-e "s,UNIT,MiB," '
                '-e "s,MEMORY,{1}," '
                '-e "s,CORES,{2}," '
                '-e "s,destroy,restart," '
                '-e "s,DISK0,{3}/{0}-0.img," '
                '-e "s,DISK1,{3}/{0}-1.img," '
                '{4}/vms/{0}.xml'.format(compute, compute_memory,
                    compute_system_cores, libvirt_images_path, THIS_PATH),
                raise_exception=True)

            # creating the computes according to the XML, the following command
            # create a domain but it does not start it and makes it persistent
            # even after shutdown
            bash.run_command('sudo virsh define {0}/vms/{1}.xml'.format(
                THIS_PATH, compute))

    if 'Storages' in configurations:
        for storage, values in configurations.get('Storages').items():
            # iterating over the storage
            storage_partition_a = int(values.get('partition_a'))
            storage_partition_b = int(values.get('partition_b'))
            storage_memory = int(values.get('memory_size'))
            storage_system_cores = int(values.get('system_cores'))

            # copy the storage.xml to vms folder
            origin = os.path.join(THIS_PATH, 'storage.xml')
            destination = os.path.join(THIS_PATH,
                'vms', '{}.xml'.format(storage))

            copy(origin, destination)

            # creating both storage's partitions in the system
            bash.run_command(
                'sudo qemu-img create -f qcow2 {0}/{1}-0.img {2}G'.format(
                    libvirt_images_path, storage, storage_partition_a),
                raise_exception=True)
            bash.run_command(
                'sudo qemu-img create -f qcow2 {0}/{1}-1.img {2}G'.format(
                    libvirt_images_path, storage, storage_partition_b),
                raise_exception=True)

            # modifying xml storage parameters
            bash.run_command(
                'sed -i -e "s,NAME,{0}," '
                '-e "s,UNIT,MiB," '
                '-e "s,MEMORY,{1}," '
                '-e "s,CORES,{2}," '
                '-e "s,destroy,restart," '
                '-e "s,DISK0,{3}/{0}-0.img," '
                '-e "s,DISK1,{3}/{0}-1.img," '
                '{4}/vms/{0}.xml'.format(storage, storage_memory,
                    storage_system_cores, libvirt_images_path, THIS_PATH),
                raise_exception=True)

            # creating the storage according to the XML, the following command
            # create a domain but it does not start it and makes it persistent
            # even after shutdown
            bash.run_command('sudo virsh define {0}/vms/{1}.xml'.format(
                THIS_PATH, storage))

    # opening the graphical interface
    if bash.is_process_running('virt-manager'):
        # in order that virt-manager takes the new configurations from the yaml
        # file, is needed to kill it and start again.
        LOG.info('Virtual Machine Manager is active, killing it ...')
        bash.run_command('sudo kill -9 $(pgrep -x virt-manager)',
                         raise_exception=True)

    # opening Virtual Machine Manager
    bash.run_command('sudo virt-manager', raise_exception=True)
    # opening the controller console
    bash.run_command('virt-manager -c qemu:///system --show-domain-console '
                     'controller-0', raise_exception=True)
    exit_dict_status(0)


def setup_qemu(iso_file, configuration_file):
    """Setup StarlingX

    The aim of this function is to setup StarlingX in a smart way in order
    to avoid configuration issues.

    :param iso_file: the iso file to be configured in the controller(s).
    :param configuration_file: the yaml configuration file.
    """
    # before to run anything, KVM needs to be checked it this is present in the
    # current host
    check_kernel_virtualization()

    # check the host requirements
    check_preconditions()

    # loading all the configurations from yaml file
    configurations = yaml.safe_load(open(configuration_file))

    # fixme(Humberto): check_system_resources is commented out due
    # check is giving problems when configuring an instance on qemu virtual
    # machine, for now this will be commented until more investigation is done

    # this part will check the values given in the yaml
    # check_system_resources(configurations)

    # setting the controller/computes nodes
    setup_controller_computes(iso_file, configurations)


def arguments():
    """Provides a set of arguments

    Defined arguments must be specified in this function in order to interact
    with the others functions in this module.
    """

    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter, description='''
Program description:
This is a tool for setup virtual environments with libvirt/Qemu in the host.
maintainer : humberto.i.perez.rodriguez@intel.com''',
        epilog='StarlingX |https://opendev.org/starlingx/test/',
        usage='%(prog)s [options]')
    group_mandatory = parser.add_argument_group('mandatory arguments')
    group_mandatory.add_argument(
        '-i', '--iso', dest='iso', required=True,
        help='the iso file to be setup in the controller')
    parser.add_argument(
        '-c', '--configuration', dest='configuration',
        help='the Qemu configuration file in yaml format. The default '
             'configuration file is qemu_setup.yaml in this folder')
    args = parser.parse_args()

    # checks if the iso file given exists
    if not os.path.isfile(args.iso):
        print('{0}: does not exists, please verify it'.format(args.iso))
        exit_dict_status(1)

    # checks if the configuration exists
    configuration_file = os.path.join(THIS_PATH, 'qemu_setup.yaml')
    if args.configuration:
        configuration_file = args.configuration

    if not os.path.exists(configuration_file):
        print('{0}: does not exists, please verify it'.format(
            configuration_file))
        exit_dict_status(1)

    setup_qemu(args.iso, configuration_file)


if __name__ == '__main__':
    arguments()

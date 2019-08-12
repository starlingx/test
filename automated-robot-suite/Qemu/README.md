[qemu_logo]: ./images/qemu_logo.png

![alt text][qemu_logo]

Table of Contents

- [qemu_setup.yml](#qemu_setupyml)
- [Description](#description)
- [Examples](#examples)
  - [1 controller + 2 compute](#1-controller--2-computes)
    - [parameters](#parameters)
  - [1 controller + 2 computes & 1 controller + 1 compute](#1-controller--2-computes--1-controller--1-compute)
  - [Highlights](#highlights)
  - [general_system_configurations section](#general_system_configurations-section)

# qemu_setup.yml
The purpose of this configurations file is to setup easily QEMU in the host.

# Description
YAML is a human-readable data serialization format that takes concepts from
programming languages such as C, Perl, and Python, and ideas from XML and the
data format of electronic mail.
It is available for several programming languages.

# Examples

## 1 controller + 2 computes
Please consider the following example to setup the following configuration:

`1 controller + 2 computes`

```yaml
configuration_0:
  controller-0:
    controller_0_partition_a: 20
    controller_0_partition_b: 10
    controller_0_memory_size: 5120
    controller_0_system_cores: 2
  controller-0-compute-0:
    controller_0_compute_0_partition_a: 20
    controller_0_compute_0_partition_b: 20
    controller_0_compute_0_memory_size: 3072
    controller_0_compute_0_system_cores: 1
  controller-0-compute-1:
    controller_0_compute_1_partition_a: 20
    controller_0_compute_1_partition_b: 20
    controller_0_compute_1_memory_size: 3072
    controller_0_compute_1_system_cores: 1
````

### parameters

**`@param: configuration_0`**: which contains the controller and the computes.<br>

**`@param: controller-0`**: which contains the following:<br>
- `@param: controller_0_partition_a`: which is the controller 0 partition size
    A in GB.
- `@param: controller_0_partition_b`: which is the controller 0 partition size
    B size in GB.
- `@param: controller_0_memory_size`: which is the controller 0 memory size
    in MB.
- `@param: controller_0_system_cores`: which is the controller 0 system cores
    to be assigned.

**`@param: controller-0-compute-0`**: which contains the following:<br>
- `@param: controller_0_compute_0_partition_a`: which is the controller's
    compute 0 partition size A in GB.
- `@param: controller_0_compute_0_partition_b`: which is the controller's
    compute 0 partition size B in GB.
- `@param: controller_0_compute_0_memory_size`: which is the controller's
    compute 0 memory size B in MB.
- `@param: controller_0_compute_0_system_cores`: which is the controller's
    compute 0 system cores to be assigned.

**`@param: controller-0-compute-1`**: which contains the following:<br>
- `@param: controller_0_compute_1_partition_a`: which is the controller's
    compute 1 partition size A in GB.
- `@param: controller_0_compute_1_partition_b`: which is the controller's
    compute 1 partition size B in GB.
- `@param: controller_0_compute_1_memory_size`: which is the controller's
    compute 1 memory size B in MB.
- `@param: controller_0_compute_1_system_cores`: which is the controller's
    compute 1 system cores to be assigned.

## 1 controller + 2 computes & 1 controller + 1 compute
Please consider the following example to setup the following configuration:

`1 controller + 2 computes & 1 controller + 1 compute`

```yaml
configuration_0:
  controller-0:
    controller_0_partition_a: 20
    controller_0_partition_b: 10
    controller_0_memory_size: 5120
    controller_0_system_cores: 2
  controller-0-compute-0:
    controller_0_compute_0_partition_a: 20
    controller_0_compute_0_partition_b: 20
    controller_0_compute_0_memory_size: 3072
    controller_0_compute_0_system_cores: 1
  controller-0-compute-1:
    controller_0_compute_1_partition_a: 20
    controller_0_compute_1_partition_b: 20
    controller_0_compute_1_memory_size: 3072
    controller_0_compute_1_system_cores: 1
configuration_1:
  controller-1:
    controller_1_partition_a: 15
    controller_1_partition_b: 10
    controller_1_memory_size: 5120
    controller_1_system_cores: 2
  controller-1-compute-0:
    controller_1_compute_0_partition_a: 20
    controller_1_compute_0_partition_b: 20
    controller_1_compute_0_memory_size: 3072
    controller_1_compute_0_system_cores: 1
```

:notebook: the parameters description are the same that the [section above](#parameters).

## Highlights
Please consider the following when creating the yaml configuration file:

- The total sum of the partitions must not exceed of the total free disk space
    in the host.
- The total sum of the memory size must not exceed of the total free memory
    size in the host.
- The total sum of the system cores must not exceed of the total system cores
    subtracting the `os_system_cores` assigned in `general_system_configurations`
    section.


## general_system_configurations section
The general_system_configurations will be explained below:

```yaml
general_system_configurations:
  os_system_memory: 1024
  disk_space_allocated_to_os: 20
  os_system_cores: 2
  default_mount_point: '/'
```

**`@param: general_system_configurations`**: which contains the following:
- `@param: os_system_memory`: which is the system memory reserved for the OS.
- `@param: disk_space_allocated_to_os`: which is the disk space reserved for
    the OS.
- `@param: os_system_cores`: which is the system cores reserved for the OS.
- `@param: default_mount_point`: which is the mount point where the space in
    disk will be analyzed by the script.

:notebook: The first 3 params are used for system reservation and they are for
the user's consideration in order to avoid that QEMU takes all the resources
making slow the current system.
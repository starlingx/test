#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


class SkipStorageSpace:
    SMALL_CINDER_VOLUMES_POOL = "Cinder Volumes Pool is less than 30G"
    INSUFFICIENT_IMG_CONV = 'Insufficient image-conversion space to convert ' \
                            '{} image to raw format'


class SkipStorageBacking:
    LESS_THAN_TWO_HOSTS_WITH_BACKING = "Less than two hosts with {} instance " \
                                       "storage backing exist on system"
    NO_HOST_WITH_BACKING = "No host with {} instance storage backing exists " \
                           "on system"


class SkipHypervisor:
    LESS_THAN_TWO_HYPERVISORS = "Less than two hypervisors available"


class SkipHyperthreading:
    LESS_THAN_TWO_HT_HOSTS = "Less than two hyperthreaded hosts available"
    MORE_THAN_ONE_HT_HOSTS = "More than one hyperthreaded hosts available"


class SkipHostIf:
    PCI_IF_UNAVAIL = "SRIOV or PCI-passthrough interface unavailable"
    PCIPT_IF_UNAVAIL = "PCI-passthrough interface unavailable"
    SRIOV_IF_UNAVAIL = "SRIOV interface unavailable"
    MGMT_INFRA_UNAVAIL = 'traffic control class is not defined in this lab'


class SkipSysType:
    SMALL_FOOTPRINT = "Skip for small footprint lab"
    LESS_THAN_TWO_CONTROLLERS = "Less than two controllers on system"
    SIMPLEX_SYSTEM = 'Not applicable to Simplex system'
    SIMPLEX_ONLY = 'Only applicable to Simplex system'

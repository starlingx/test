#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


from copy import deepcopy

VALID_SCOPES = ['function', 'class', 'module', 'session']
_RESOURCE_TYPES = ['vm', 'volume', 'volume_type', 'volume_qos',
                   'flavor', 'image', 'server_group', 'router',
                   'subnet', 'floating_ip', 'heat_stack', 'port',
                   'trunk', 'network', 'security_group_rule'
                   'security_group', 'network_qos', 'vol_snapshot', 'aggregate',
                   'port_pair', 'port_pair_group', 'flow_classifier',
                   'port_chain', 'datanetwork', 'providernet']

_RESOURCE_DICT = {key: [] for key in _RESOURCE_TYPES+['vm_with_vol']}


def _check_values(value, val_type='scope', valid_vals=None):
    value = value.lower()
    if not valid_vals:
        valid_vals = VALID_SCOPES
    if value not in valid_vals:
        raise ValueError("'{}' param value has to be one of the: "
                         "{}".format(val_type, valid_vals))


class ResourceCleanup:
    """
    Class to hold the cleanup list and related functions.
    """

    __resources_to_cleanup = \
        {key_: deepcopy(_RESOURCE_DICT) for key_ in VALID_SCOPES}

    @classmethod
    def _get_resources(cls, scope):
        return cls.__resources_to_cleanup[scope]

    @classmethod
    def _reset(cls, scope):
        for key in cls.__resources_to_cleanup[scope]:
            cls.__resources_to_cleanup[scope][key] = []

    @classmethod
    def add(cls, resource_type, resource_id, scope='function',
            del_vm_vols=True):
        """
        Add resource to cleanup list.

        Args:
            resource_type (str): one of these: 'vm', 'volume', 'flavor
            resource_id (str|list): id(s) of the resource to add to cleanup list
            scope (str): when the cleanup should be done. Valid value is one of
                these: 'function', 'class', 'module'
            del_vm_vols (bool): whether to delete attached volume(s) if given
                resource is vm.

        """
        _check_values(scope)
        _check_values(resource_type, val_type='resource_type',
                      valid_vals=_RESOURCE_TYPES)

        if resource_type == 'vm' and del_vm_vols:
            resource_type = 'vm_with_vol'

        if not isinstance(resource_id, (list, tuple)):
            resource_id = [resource_id]

        for res_id in resource_id:
            cls.__resources_to_cleanup[scope][resource_type].append(res_id)

    @classmethod
    def remove(cls, resource_type, resource_id, scope='function',
               del_vm_vols=True):
        """
        Add resource to cleanup list.

        Args:
            resource_type (str): one of these: 'vm', 'volume', 'flavor
            resource_id (str|list): id(s) of the resource to add to cleanup list
            scope (str): when the cleanup should be done. Valid value is one of
                these: 'function', 'class', 'module'
            del_vm_vols (bool): whether to delete attached volume(s) if given
                resource is vm.

        """
        if scope is None:
            return

        _check_values(scope)
        _check_values(resource_type, val_type='resource_type',
                      valid_vals=_RESOURCE_TYPES)

        if resource_type == 'vm' and del_vm_vols:
            resource_type = 'vm_with_vol'

        if not isinstance(resource_id, (list, tuple)):
            resource_id = [resource_id]

        existing_list = cls.__resources_to_cleanup[scope][resource_type]
        for res_id in resource_id:
            if res_id in existing_list:
                existing_list.remove(res_id)


class VlmHostsReserved:
    __hosts_reserved_dict = {key: [] for key in VALID_SCOPES}

    @classmethod
    def _reset(cls, scope):
        cls.__hosts_reserved_dict[scope] = []

    @classmethod
    def _get_hosts_reserved(cls, scope):
        return list(cls.__hosts_reserved_dict[scope])

    @classmethod
    def add(cls, hosts, scope='session'):
        """
        Add resource to cleanup list.

        Args:
            hosts (str|list): hostname(s)
            scope (str): one of these: 'function', 'class', 'module', 'session'

        """
        _check_values(scope)

        if not isinstance(hosts, (list, tuple)):
            hosts = [hosts]

        for host in hosts:
            cls.__hosts_reserved_dict[scope].append(host)


class GuestLogs:
    __guests_to_collect = {key: [] for key in VALID_SCOPES}

    @classmethod
    def _reset(cls, scope):
        cls.__guests_to_collect[scope] = []

    @classmethod
    def remove(cls, vm_id):
        """
        Remove a guest from collect log list. Call this if test passed.

        Args:
            vm_id (str): vm to remove from collection list

        """
        for scope in VALID_SCOPES:
            try:
                cls.__guests_to_collect[scope].remove(vm_id)
            except ValueError:
                continue

    @classmethod
    def _get_guests(cls, scope):
        return list(cls.__guests_to_collect[scope])

    @classmethod
    def add(cls, vm_id, scope='function'):
        """
        Add a guest to collect log list. Applicable to guest heartbeat,
        server group, vm scaling test cases.
            - Use fixture_resources.GuestLogs.add() to add a guest to collect
                list
            - Use fixture_resources.GuestLogs.remove() to remove a guest
                from collect list if test passed

        Args:
            vm_id (str): vm to add to collection list
            scope (str): one of these: 'function', 'class', 'module', 'session'

        """
        _check_values(scope)

        if vm_id not in cls.__guests_to_collect[scope]:
            cls.__guests_to_collect[scope].append(vm_id)

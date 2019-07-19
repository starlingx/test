#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


# Please DO NOT import any modules


class ProjVar:
    __var_dict = {'BUILD_PATH': None,
                  'LOG_DIR': None,
                  'SOURCE_OPENRC': False,
                  'SW_VERSION': [],
                  'PATCH': None,
                  'SESSION_ID': None,
                  'CGCS_DB': True,
                  'IS_SIMPLEX': False,
                  'KEYSTONE_DEBUG': False,
                  'TEST_NAME': None,
                  'PING_FAILURE': False,
                  'LAB': None,
                  'ALWAYS_COLLECT': False,
                  'REGION': 'RegionOne',
                  'COLLECT_TELNET': False,
                  'TELNET_THREADS': None,
                  'SYS_TYPE': None,
                  'COLLECT_SYS_NET_INFO': False,
                  'IS_VBOX': False,
                  'RELEASE': 'R6',
                  'REMOTE_CLI': False,
                  'USER_FILE_DIR': '~/',
                  'NO_TEARDOWN': False,
                  'VSWITCH_TYPE': None,
                  'IS_DC': False,
                  'PRIMARY_SUBCLOUD': None,
                  'BUILD_INFO': {},
                  'TEMP_DIR': '',
                  'INSTANCE_BACKING': {},
                  'OPENSTACK_DEPLOYED': None,
                  'DEFAULT_INSTANCE_BACKING': None,
                  'STX_KEYFILE_PATH': '~/.ssh/id_rsa'
                  }

    @classmethod
    def init_vars(cls, lab, natbox, logdir, tenant, collect_all, always_collect,
                  horizon_visible):

        labname = lab['short_name']

        cls.__var_dict.update(**{
            'NATBOX_KEYFILE_PATH': '~/priv_keys/keyfile_{}.pem'.format(labname),
            'STX_KEYFILE_SYS_HOME': '~/keyfile_{}.pem'.format(labname),
            'LOG_DIR': logdir,
            'TCLIST_PATH': logdir + '/test_results.log',
            'PYTESTLOG_PATH': logdir + '/pytestlog.log',
            'LAB_NAME': lab['short_name'],
            'TEMP_DIR': logdir + '/tmp_files/',
            'PING_FAILURE_DIR': logdir + '/ping_failures/',
            'GUEST_LOGS_DIR': logdir + '/guest_logs/',
            'PRIMARY_TENANT': tenant,
            'LAB': lab,
            'NATBOX': natbox,
            'COLLECT_ALL': collect_all,
            'ALWAYS_COLLECT': always_collect,
            'HORIZON_VISIBLE': horizon_visible
        })

    @classmethod
    def set_var(cls, append=False, **kwargs):
        for key, val in kwargs.items():
            if append:
                cls.__var_dict[key.upper()].append(val)
            else:
                cls.__var_dict[key.upper()] = val

    @classmethod
    def get_var(cls, var_name):
        var_name = var_name.upper()
        valid_vars = cls.__var_dict.keys()
        if var_name not in valid_vars:
            raise ValueError(
                "Invalid var_name: {}. Valid vars: {}".format(var_name,
                                                              valid_vars))

        return cls.__var_dict[var_name]

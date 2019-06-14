#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


class Labs:
    # Place for existing stx systems for convenience.
    # --lab <short_name> can be used in cmdline specify an existing system

    EXAMPLE = {
        'short_name': 'my_server',
        'name': 'my_server.com',
        'floating ip': '10.10.10.2',
        'controller-0 ip': '10.10.10.3',
        'controller-1 ip': '10.10.10.4',
    }


def update_lab(lab_dict_name=None, lab_name=None, floating_ip=None, **kwargs):
    """
    Update/Add lab dict params for specified lab
    Args:
        lab_dict_name (str|None):
        lab_name (str|None): lab short_name. This is used only if
        lab_dict_name is not specified
        floating_ip (str|None):
        **kwargs: Some possible keys: subcloud-1, name, etc

    Returns (dict): updated lab dict

    """

    if not lab_name and not lab_dict_name:
        from consts.proj_vars import ProjVar
        lab_name = ProjVar.get_var('LAB').get('short_name', None)
        if not lab_name:
            raise ValueError("lab_dict_name or lab_name needs to be specified")

    if floating_ip:
        kwargs.update(**{'floating ip': floating_ip})

    if not kwargs:
        raise ValueError("Please specify floating_ip and/or kwargs")

    if not lab_dict_name:
        attr_names = [attr for attr in dir(Labs) if not attr.startswith('__')]
        lab_names = [getattr(Labs, attr).get('short_name') for attr in
                     attr_names]
        lab_index = lab_names.index(lab_name.lower().strip())
        lab_dict_name = attr_names[lab_index]
    else:
        lab_dict_name = lab_dict_name.upper().replace('-', '_')

    lab_dict = getattr(Labs, lab_dict_name)
    lab_dict.update(kwargs)
    return lab_dict


def get_lab_dict(lab, key='short_name'):
    """

    Args:
        lab: lab name or fip
        key: unique identifier to locate a lab. Valid values: short_name,
        name, floating ip

    Returns (dict|None): lab dict or None if no matching lab found
    """
    __lab_attr_list = [attr for attr in dir(Labs) if not attr.startswith('__')]
    __lab_list = [getattr(Labs, attr) for attr in __lab_attr_list]
    __lab_list = [lab for lab in __lab_list if isinstance(lab, dict)]

    lab_info = None
    for lab_ in __lab_list:
        if lab.lower().replace('-', '_') == lab_.get(key).lower().replace('-',
                                                                          '_'):
            lab_info = lab_
            break

    return lab_info


def add_lab_entry(floating_ip, dict_name=None, short_name=None, name=None,
                  **kwargs):
    """
    Add a new lab dictionary to Labs class
    Args:
        floating_ip (str): floating ip of a lab to be added
        dict_name: name of the entry, such as 'PV0'
        short_name: short name of the TiS system, such as ip_1_4
        name: name of the STX system, such as 'yow-cgcs-pv-0'
        **kwargs: other information of the lab such as controllers' ips, etc

    Returns:
        dict: lab dict added to Labs class

    """
    for attr in dir(Labs):
        lab = getattr(Labs, attr)
        if isinstance(lab, dict):
            if lab['floating ip'] == floating_ip:
                raise ValueError(
                    "Entry for {} already exists in Labs class!".format(
                        floating_ip))

    if dict_name and dict_name in dir(Labs):
        raise ValueError(
            "Entry for {} already exists in Labs class!".format(dict_name))

    if not short_name:
        short_name = floating_ip

    if not name:
        name = floating_ip

    if not dict_name:
        dict_name = floating_ip

    lab_dict = {'name': name,
                'short_name': short_name,
                'floating ip': floating_ip,
                }

    lab_dict.update(kwargs)
    setattr(Labs, dict_name, lab_dict)
    return lab_dict


class NatBoxes:
    # Place for existing NatBox that are already configured
    NAT_BOX_HW_EXAMPLE = {
        'name': 'nat_hw',
        'ip': '10.10.10.10',
        'user': 'natbox_user',
        'password': 'natbox_password'
    }

    # Following example when localhost is configured as natbox, and test cases
    # are also ran from same localhost
    NAT_BOX_VBOX_EXAMPLE = {
        'name': 'localhost',
        'ip': 'localhost',
        'user': None,
        'password': None,
    }

    @staticmethod
    def add_natbox(ip, user=None, password=None, prompt=None):
        user = user if user else 'svc-cgcsauto'
        password = password if password else ')OKM0okm'

        nat_dict = {'ip': ip,
                    'name': ip,
                    'user': user,
                    'password': password,
                    }
        if prompt:
            nat_dict['prompt'] = prompt
        setattr(NatBoxes, 'NAT_NEW', nat_dict)
        return nat_dict

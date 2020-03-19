#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#


import requests
import json
import os

from consts.proj_vars import ProjVar
from consts.auth import CliAuth, Tenant, HostLinuxUser
from keywords import keystone_helper, security_helper

from utils.tis_log import LOG


class Rest:
    """
        Base rest Class that uses requests

        Supports;
            Basic REST invocations with requests
            generate_token_request   generates generic token request
            retrieve_token           actually receive token
            auth_header_select       utility function to switch auth.
            get                      perform HTTP GET
            delete                   perform HTTP DELETE
            patch                    perform HTTP PATCH
            put                      perform HTTP PUT
            post                     perform HTTP POST
    """

    def __init__(self, serviceName, platform=False):
        """
        Initiate an object for handling REST calls.
        Args:
            serviceName -

        """
        auth_info = Tenant.get('admin_platform') if platform else Tenant.get(
            'admin')
        self.token = ""
        self.token_payload = ""
        self.region = ProjVar.get_var('REGION')
        self.baseURL = keystone_helper.get_endpoints(field='URL',
                                                     service_name=serviceName,
                                                     interface="public",
                                                     region=self.region,
                                                     auth_info=auth_info)[0]
        self.ksURL = keystone_helper.get_endpoints(field='URL',
                                                   service_name='keystone',
                                                   interface="public",
                                                   region=self.region,
                                                   auth_info=auth_info)[0]
        self.cert_path = None
        self.verify = True
        self.is_https = CliAuth.get_var('HTTPS')
        if self.is_https:
            self.verify = False
            cert_path = os.path.join(ProjVar.get_var('TEMP_DIR'),
                                     'server-with-key.pem')
            if not os.path.exists(cert_path):
                cert_path = security_helper.fetch_cert_file(scp_to_local=True)
            self.cert_path = cert_path
            if cert_path:
                self.verify = cert_path

        self.generate_token_request()
        self.retrieve_token('/auth/tokens')

    def generate_token_request(self, **kwargs):
        """
        TBD - should update this to allow for configurable
              json_string to be able to change any value
              for truly flexible testing.
        """
        json_string = ('{"auth":'
                       '{"identity":{"methods": ["password"],'
                       '"password": {"user": {"domain":'
                       '{"name": "Default"},"name":'
                       '"admin","password":"St8rlingX*"}}},'
                       '"scope":{"project": {"name":'
                       '"admin","domain": {"name":"Default"}'
                       '}}}}')
        self.token_payload = json.loads(json_string)

    def retrieve_token(self, endpoint, token_request=None, verify=None):
        if token_request is None:
            token_request = json.dumps(self.token_payload)

        headers = {'Content-type': 'application/json'}

        if verify is None:
            verify = self.verify

        LOG.info("Retrieving token. post URL: {}, headers: {}, data: {}".format(
            self.ksURL + endpoint, headers,
            token_request))
        r = requests.post(self.ksURL + endpoint,
                          headers=headers,
                          data=token_request, verify=verify)
        req = r.request
        print("teststestst \n{} {}\n{}\n\n{}".format(req.method, req.url,
                                                     '\n'.join(
                                                         '{}: {}'.format(k, v)
                                                         for k, v in
                                                         req.headers.items()),
                                                     req.body, ))

        if r.status_code != 201:
            self.token = "THISTOKENDOESNOTEXIST"
        else:
            self.token = r.headers['X-Subject-Token']
        LOG.info(
            'token retrieval status: {} text: {}'.format(r.status_code, r.text))
        return r.status_code, r.text

    def auth_header_select(self, auth=True):
        if auth:
            headers = {'X-Auth-Token': self.token}
        else:
            headers = {'X-Auth-Token': "THISISNOTAVALIDTOKEN"}
        return headers

    def get(self, resource="", auth=True, verify=None):
        """

        Args:
            resource:
            auth:
            verify (bool|str|None):
                True: applies to non-https system
                False: equivalent to --insecure in curl cmd
                str: applies to https system. CA-Certificate path. e.g.,
                verify=/path/to/cert
                None: Automatically set verify value based on whether https
                is enabled.

        Returns:

        """
        headers = self.auth_header_select(auth)
        message = "baseURL: {} resource: {} headers: {}"
        LOG.info(message.format(self.baseURL, resource, headers))
        if verify is None:
            verify = self.verify
        r = requests.get(self.baseURL + resource,
                         headers=headers, verify=verify)
        return r.status_code, r.json()

    def delete(self, resource="", auth=True, verify=None):
        headers = self.auth_header_select(auth)
        message = "baseURL: {} resource: {} headers: {}"
        LOG.debug(message.format(self.baseURL, resource, headers))
        if verify is None:
            verify = self.verify
        r = requests.delete(self.baseURL + resource,
                            headers=headers, verify=verify)
        return r.status_code, r.json()

    def patch(self, resource="", json_data={}, auth=True, verify=None):
        headers = self.auth_header_select(auth)
        message = "baseURL: {} resource: {} headers: {} data: {}"
        LOG.debug(message.format(self.baseURL, resource,
                                 headers, json_data))
        if verify is None:
            verify = self.verify
        r = requests.patch(self.baseURL + resource,
                           headers=headers, data=json_data,
                           verify=verify)
        return r.status_code, r.json()

    def put(self, resource="", json_data={}, auth=True, verify=None):
        headers = self.auth_header_select(auth)
        message = "baseURL: {} resource: {} headers: {} data: {}"
        LOG.debug(message.format(self.baseURL, resource,
                                 headers, json_data))
        if verify is None:
            verify = self.verify
        r = requests.put(self.baseURL + resource,
                         headers=headers, data=json_data,
                         verify=verify)
        return r.status_code, r.json()

    def post(self, resource="", json_data={}, auth=True, verify=None):
        headers = self.auth_header_select(auth)
        message = "baseURL: {} resource: {} headers: {} data: {}"
        LOG.debug(message.format(self.baseURL, resource,
                                 headers, json_data))
        if verify is None:
            verify = self.verify
        r = requests.post(self.baseURL + resource,
                          headers=headers, data=json_data,
                          verify=verify)
        return r.status_code, r.json()


def check_url(url, fail=False, secure=False):
    """
    Checks the access to the given url and returns True or False based on fail condition
    Args:
        url(str): url to check the access
        fail(boolean): True or False
        secure(boolean): default is False for
                        both http and https protocol
    Return(boolean):
        returns True or False based on expected behaviour
    """
    try:
        r = requests.get(url, timeout=10, verify=secure)
        return True if r.status_code == 200 and fail is False else False
    except requests.exceptions.Timeout:
        return True if fail else False

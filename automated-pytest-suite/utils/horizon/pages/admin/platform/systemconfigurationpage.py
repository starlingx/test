from utils.horizon.pages import basepage
from utils.horizon.regions import forms, tables, messages
from utils import exceptions
from utils.tis_log import LOG


class SystemsTable(tables.TableRegion):
    name = "systems"

    EDIT_SYSTEM_FORM_FIELDS = ("name", "description")
    SYSTEMS_MAP = {
        'name': 'Name',
        'system_type': 'System Type',
        'system_mode': 'System Mode',
        'description': 'Description',
        'software_version': 'Version'
    }

    @tables.bind_row_action('update')
    def edit_system(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_SYSTEM_FORM_FIELDS)


class AddressPoolsTable(tables.TableRegion):
    name = "address_pools"

    ADDRESS_POOL_FORM_FIELDS = ("name", "network", "order", "ranges")

    @tables.bind_table_action('create')
    def create_address_pool(self, create_button):
        create_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.ADDRESS_POOL_FORM_FIELDS)

    @tables.bind_table_action('delete')
    def delete_address_pool(self, delete_button):
        delete_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('update')
    def update_address_pool(self, update_button, row):
        update_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.ADDRESS_POOL_FORM_FIELDS)


class DNSTable(tables.TableRegion):
    name = "cdns_table"

    EDIT_DNS_FORM_FIELDS = ("NAMESERVER_1", "NAMESERVER_2", "NAMESERVER_3")
    PTP_MAP = {
        'enabled': 'PTP Enabled',
        'mode': 'PTP Time Stamping Mode',
        'transport': 'PTP Network Transport',
        'mechanism': 'PTP Delay Mechanism'
    }

    @tables.bind_table_action('update_cdns')
    def edit_dns(self, edit_button):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_DNS_FORM_FIELDS)


class NTPTable(tables.TableRegion):
    name = "cntp_table"

    EDIT_NTP_FORM_FIELDS = ("NTP_SERVER_1", "NTP_SERVER_2", "NTP_SERVER_3")

    @tables.bind_table_action('update_cntp')
    def edit_ntp(self, edit_button):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_NTP_FORM_FIELDS)


class PTPTable(tables.TableRegion):
    name = "cptp_table"

    EDIT_PTP_FORM_FIELDS = ("mode", "transport", "mechanism")
    PTP_MAP = {
        'enabled': 'PTP Enabled',
        'mode': 'PTP Time Stamping Mode',
        'transport': 'PTP Network Transport',
        'mechanism': 'PTP Delay Mechanism',
    }

    @tables.bind_table_action('update_cptp')
    def edit_ptp(self, edit_button):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_PTP_FORM_FIELDS)


class OAMTable(tables.TableRegion):
    name = "coam_table"

    EDIT_OAM_FORM_FIELDS = ("EXTERNAL_OAM_SUBNET", "EXTERNAL_OAM_GATEWAY_ADDRESS",
                            "EXTERNAL_OAM_FLOATING_ADDRESS", "EXTERNAL_OAM_0_ADDRESS",
                            "EXTERNAL_OAM_1_ADDRESS")
    SIMPLEX_OAM_MAP = {
        'oam_subnet': 'OAM Subnet',
        'oam_ip': 'OAM IP',
        'oam_gateway_ip': 'OAM Gateway IP'
    }
    OAM_MAP = {
        'oam_subnet': 'OAM Subnet',
        'oam_floating_ip': 'OAM Floating IP',
        'oam_gateway_ip': 'OAM Gateway IP',
        'oam_c0_ip': 'OAM controller-0 IP',
        'oam_c1_ip': 'OAM controller-1 IP'
    }

    @tables.bind_table_action('update_coam')
    def edit_oam(self, edit_button):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_OAM_FORM_FIELDS)


class ControlerfsTable(tables.TableRegion):
    name = "storage_table"

    EDIT_FILESYSTEM_FORM_FIELDS = ("database", "glance", "backup", "scratch",
                                   "extension", "img_converstions", "ceph_mon")
    CONTROLERFS_MAP = {
        'name': 'Storage Name',
        'size': 'Size (GiB)'
    }

    @tables.bind_table_action('update_storage')
    def edit_filesystem(self, edit_button):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_FILESYSTEM_FORM_FIELDS)


class CephStoragePoolsTable(tables.TableRegion):
    name = "storage_pools_table"

    EDIT_POOL_QUOTAS_FIELDS = ("cinder_pool_gib", "glance_pool_gib",
                               "ephemeral_pool_gib", "object_pool_gib")
    CEPH_STORAGE_POOLS_MAP = {
        'tier_name': 'Ceph Storage Tier',
        'cinder_pool_gib': 'Cinder Volume Storage (GiB)',
        'glance_pool_gib': 'Glance Image Storage (GiB)',
        'ephemeral_pool_gib': 'Nova Ephemeral Disk Storage (GiB)',
        'object_pool_gib': 'Object Storage (GiB)',
        'ceph_total_space_gib': 'Ceph total space (GiB)'
    }

    @tables.bind_row_action('update_storage_pools')
    def edit_ceph_storage_pools(self, edit_button, row):
        edit_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver, field_mappings=self.EDIT_POOL_QUOTAS_FIELDS)


class SystemConfigurationPage(basepage.BasePage):

    PARTIAL_URL = 'admin/system_config'
    SYSTEMS_TAB_INDEX = 0
    ADDRESS_POOLS_TAB_INDEX = 1
    DNS_TAB_INDEX = 2
    NTP_TAB_INDEX = 3
    PTP_TAB_INDEX = 4
    OAM_IP_TAB_INDEX = 5
    CONTROLLER_FILESYSTEM_TAB_INDEX = 6
    CEPH_STORAGE_POOLS_INDEX = 7
    SYSTEMS_TABLE_NAME_COLUMN = 'Name'
    ADDRESS_POOLS_TABLE_NAME_COLUMN = 'Name'
    DNS_TABLE_SERVER1_IP = 'DNS Server 1 IP'
    NTP_TABLE_SERVER1_ADDR = 'NTP Server 1 Address'
    PTP_TABLE_ENABLED = 'PTP Enabled'
    OAM_TABLE_SUBNET = 'OAM Subnet'
    CONTROLLERFS_TABLE_STORAGE_NAME = 'Storage Name'
    CEPH_STORAGE_TABLE_TIER_COLUMN = 'Ceph Storage Tier'

    @property
    def systems_table(self):
        return SystemsTable(self.driver)

    @property
    def address_pools_table(self):
        return AddressPoolsTable(self.driver)

    @property
    def dns_table(self):
        return DNSTable(self.driver)

    @property
    def ntp_table(self):
        return NTPTable(self.driver)

    @property
    def ptp_table(self):
        return PTPTable(self.driver)

    @property
    def oam_table(self):
        return OAMTable(self.driver)

    @property
    def controllerfs_table(self):
        return ControlerfsTable(self.driver)

    @property
    def ceph_storage_pools_table(self):
        return CephStoragePoolsTable(self.driver)

    def _get_row_with_system_name(self, name):
        return self.systems_table.get_row(self.SYSTEMS_TABLE_NAME_COLUMN, name)

    def get_system_info(self, name, header):
        row = self._get_row_with_system_name(name)
        return row.cells[header].text

    def _get_row_with_address_pool_name(self, name):
        return self.address_pools_table.get_row(self.ADDRESS_POOLS_TABLE_NAME_COLUMN, name)

    def get_address_pool_info(self, name, header):
        row = self._get_row_with_address_pool_name(name)
        return row.cells[header].text

    def _get_row_with_dns_server_ip(self, ip):
        return self.dns_table.get_row(self.DNS_TABLE_SERVER1_IP, ip)

    def get_dns_info(self, ip, header):
        row = self._get_row_with_dns_server_ip(ip)
        return row.cells[header].text

    def _get_row_with_ntp_server_addr(self, addr):
        return self.ntp_table.get_row(self.NTP_TABLE_SERVER1_ADDR, addr)

    def get_ntp_info(self, addr, header):
        row = self._get_row_with_ntp_server_addr(addr)
        return row.cells[header].text

    def _get_row_with_ptp_enabled(self, enabled):
        return self.ptp_table.get_row(self.PTP_TABLE_ENABLED, enabled)

    def get_ptp_info(self, enabled, header):
        row = self._get_row_with_ptp_enabled(enabled)
        return row.cells[header].text

    def _get_row_with_oam_subnet(self, subnet):
        return self.oam_table.get_row(self.OAM_TABLE_SUBNET, subnet)

    def get_oam_info(self, subnet, header):
        row = self._get_row_with_oam_subnet(subnet)
        return row.cells[header].text

    def _get_row_with_controllerfs_storage_name(self, storage_name):
        return self.controllerfs_table.get_row(self.CONTROLLERFS_TABLE_STORAGE_NAME, storage_name)

    def get_controllerfs_info(self, storage_name, header):
        row = self._get_row_with_controllerfs_storage_name(storage_name)
        return row.cells[header].text

    def _get_row_with_ceph_tier_name(self, tier_name):
        return self.ceph_storage_pools_table.get_row(self.CEPH_STORAGE_TABLE_TIER_COLUMN, tier_name)

    def get_ceph_storage_pools_info(self, tier_name, header):
        row = self._get_row_with_ceph_tier_name(tier_name)
        return row.cells[header].text

    def go_to_systems_tab(self):
        self.go_to_tab(self.SYSTEMS_TAB_INDEX)

    def go_to_address_pools_tab(self):
        self.go_to_tab(self.ADDRESS_POOLS_TAB_INDEX)

    def go_to_dns_tab(self):
        self.go_to_tab(self.DNS_TAB_INDEX)

    def go_to_ntp_tab(self):
        self.go_to_tab(self.NTP_TAB_INDEX)

    def go_to_ptp_tab(self):
        self.go_to_tab(self.PTP_TAB_INDEX)

    def go_to_oam_ip_tab(self):
        self.go_to_tab(self.OAM_IP_TAB_INDEX)

    def go_to_controller_filesystem_tab(self):
        self.go_to_tab(self.CONTROLLER_FILESYSTEM_TAB_INDEX)

    def go_to_ceph_storage_pools_tab(self):
        self.go_to_tab(self.CEPH_STORAGE_POOLS_INDEX)

    def is_systems_present(self, name):
        return bool(self._get_row_with_system_name(name))

    def create_address_pool(self, name, network, order=None, ranges=None, fail_ok=False):
        create_form = self.address_pools_table.create_address_pool()
        create_form.name.text = name
        create_form.network.text = network
        if order is not None:
            create_form.order.text = order
        if ranges is not None:
            create_form.ranges.text = ranges
        create_form.submit()
        if not self.find_message_and_dismiss(messages.SUCCESS):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to create address pool {}".format(name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "creating address pool {}".format(name))
        succ_msg = "Address pool {} is successfully created.".format(name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def delete_address_pool(self, name, fail_ok=False):
        row = self._get_row_with_address_pool_name(name)
        row.mark()
        confirm_delete_form = self.address_pools_table.delete_address_pool()
        confirm_delete_form.submit()
        if not self.find_message_and_dismiss(messages.SUCCESS):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to delete address pool {}".format(name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "deleting address pool {}".format(name))
        succ_msg = "Address pool {} is successfully deleted.".format(name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def update_address_pool(self, name, new_name=None, new_order=None, new_ranges=None, fail_ok=False):
        row = self._get_row_with_address_pool_name(name)
        edit_form = self.address_pools_table.update_address_pool(row)
        if new_name is not None:
            edit_form.name.text = new_name
        if new_order is not None:
            edit_form.order.text = new_order
        if new_ranges is not None:
            edit_form.ranges.text = new_ranges
        edit_form.submit()
        if not self.find_message_and_dismiss(messages.INFO):
            found_err = self.find_message_and_dismiss(messages.ERROR)
            if fail_ok and found_err:
                err_msg = "Failed to update address pool {}".format(name)
                LOG.info(err_msg)
                return 1, err_msg
            else:
                raise exceptions.HorizonError("No info message found after "
                                              "updating address pool {}".format(name))
        succ_msg = "Address pool {} is successfully updated.".format(name)
        LOG.info(succ_msg)
        return 0, succ_msg

    def is_address_present(self, name):
        return bool(self._get_row_with_address_pool_name(name))

    def edit_dns(self, server1=None, server2=None, server3=None, cancel=False, fail_ok=False):
        edit_form = self.dns_table.edit_dns()
        if server1 is not None:
            edit_form.NAMESERVER_1.text = server1
        if server2 is not None:
            edit_form.NAMESERVER_2.text = server2
        if server3 is not None:
            edit_form.NAMESERVER_3.text = server3
        if cancel:
            edit_form.cancel()
        else:
            edit_form.submit()
            if not self.find_message_and_dismiss(messages.SUCCESS):
                found_err = self.find_message_and_dismiss(messages.ERROR)
                if fail_ok and found_err:
                    err_msg = "Failed to edit DNS"
                    LOG.info(err_msg)
                    return 1, err_msg
                else:
                    raise exceptions.HorizonError("No info message found after editing DNS")
            succ_msg = "DNS is successfully updated."
            LOG.info(succ_msg)
            return 0, succ_msg

    def edit_ntp(self, server1=None, server2=None, server3=None, cancel=False):
        edit_form = self.ntp_table.edit_ntp()
        if server1 is not None:
            edit_form.NTP_SERVER_1.text = server1
        if server2 is not None:
            edit_form.NTP_SERVER_2.text = server2
        if server3 is not None:
            edit_form.NTP_SERVER_3.text = server3
        if cancel:
            edit_form.cancel()
        else:
            edit_form.submit()

    def edit_ptp(self, mode=None, transport=None, mechanism=None, cancel=False):
        edit_form = self.ptp_table.edit_ptp()
        if mode is not None:
            edit_form.mode.value = mode
        if transport is not None:
            edit_form.transport.value = transport
        if mechanism is not None:
            edit_form.mechanism.value = mechanism
        if cancel:
            edit_form.cancel()
        else:
            edit_form.submit()

    def edit_oam(self, subnet=None, gateway=None, floating=None,
                 controller0=None, controller1=None, cancel=False):
        edit_form = self.oam_table.edit_oam()
        if subnet is not None:
            edit_form.EXTERNAL_OAM_SUBNET.text = subnet
        if gateway is not None:
            edit_form.EXTERNAL_OAM_GATEWAY_ADDRESS.text = gateway
        if floating is not None:
            edit_form.EXTERNAL_OAM_FLOATING_ADDRESS.text = floating
        if controller0 is not None:
            edit_form.EXTERNAL_OAM_0_ADDRESS.text = controller0
        if controller1 is not None:
            edit_form.EXTERNAL_OAM_1_ADDRESS.text = controller1
        if cancel:
            edit_form.cancel()
        else:
            edit_form.submit()

    def edit_filesystem(self, database=None, glance=None, backup=None,
                        scratch=None, extension=None, img_conversions=None,
                        cancel=False):
        edit_form = self.controllerfs_table.edit_filesystem()
        if database is not None:
            edit_form.database.value = database
        if glance is not None:
            edit_form.glance.value = glance
        if backup is not None:
            edit_form.backup.value = backup
        if scratch is not None:
            edit_form.scratch.value = scratch
        if extension is not None:
            edit_form.extension.value = extension
        if img_conversions is not None:
            edit_form.img_conversions.value = img_conversions
        if cancel:
            edit_form.cancel()
        else:
            edit_form.submit()

    def edit_storage_pool(self, tier_name, cinder_pool=None, glance_pool=None,
                          ephemeral_pool=None, object_pool=None, cancel=False):
        row = self._get_row_with_ceph_tier_name(tier_name)
        edit_form = self.ceph_storage_pools_table.edit_ceph_storage_pools(row)
        if cinder_pool is not None:
            edit_form.cinder_pool_gib.value = cinder_pool
        if glance_pool is False:
            edit_form.glance_pool_gib.value = glance_pool
        if ephemeral_pool is True:
            edit_form.ephemeral_pool_gib = ephemeral_pool
        if object_pool is not None:
            edit_form.object_pool_gib.value = object_pool
        if cancel:
            edit_form.cancel()
        else:
            edit_form.submit()

    def check_horizon_displays(self, expt_horizon, table_name):
        horizon_value = None
        for horizon_header in expt_horizon:
            if table_name == self.systems_table.name:
                horizon_value = self.get_system_info(name=expt_horizon['Name'],
                                                     header=horizon_header)
            elif table_name == self.address_pools_table.name:
                horizon_value = self.get_address_pool_info(
                    name=expt_horizon['Name'], header=horizon_header)
            elif table_name == self.ptp_table.name:
                horizon_value = self.get_ptp_info(
                    enabled=expt_horizon['PTP Enabled'], header=horizon_header)
            elif table_name == self.oam_table.name:
                horizon_value = self.get_oam_info(
                    subnet=expt_horizon['OAM Subnet'], header=horizon_header)
            elif table_name == self.controllerfs_table.name:
                horizon_value = self.get_controllerfs_info(
                    storage_name=expt_horizon['Storage Name'], header=horizon_header)
            elif table_name == self.ceph_storage_pools_table.name:
                horizon_value = self.get_ceph_storage_pools_info(
                    tier_name=expt_horizon['Ceph Storage Tier'], header=horizon_header)
            if str(expt_horizon[horizon_header]) != horizon_value:
                err_msg = '{} display incorrectly'.format(horizon_header)
                raise exceptions.HorizonError(err_msg)
        succ_msg = 'All content display correctly'
        LOG.info(succ_msg)

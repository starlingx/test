import re

from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.regions import forms
from utils.horizon.regions import tables


class FloatingIPTable(tables.TableRegion):
    name = 'floating_ips'
    ALLOCATE_IP_FORM_FIELDS = ("pool", "tenant", "floating_ip_address")
    FLOATING_IP_ASSOCIATIONS_FORM_FIELDS = ("ip_id", "instance_id")

    @tables.bind_table_action('allocate')
    def allocate_ip(self, allocate_button):
        allocate_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.ALLOCATE_IP_FORM_FIELDS)

    @tables.bind_table_action('release')
    def release_ip(self, release_button):
        release_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('release')
    def release_ip_by_row(self, release_button, row):
        release_button.click()
        return forms.BaseFormRegion(self.driver)

    @tables.bind_row_action('associate')
    def associate_ip(self, associate_button, row):
        associate_button.click()
        self.wait_till_spinner_disappears()
        return forms.FormRegion(self.driver,
                                field_mappings=self.FLOATING_IP_ASSOCIATIONS_FORM_FIELDS)

    @tables.bind_row_action('disassociate')
    def disassociate_ip(self, disassociate_button, row):
        disassociate_button.click()
        self.wait_till_spinner_disappears()
        return forms.BaseFormRegion(self.driver)


class FloatingipsPage(basepage.BasePage):
    PARTIAL_URL = 'project/floating_ips'
    FLOATING_IPS_TABLE_IP_COLUMN = 'IP Address'

    _floatingips_fadein_popup_locator = (
        by.By.CSS_SELECTOR, '.alert.alert-success.alert-dismissable.fade.in>p')

    def _get_row_with_floatingip(self, floatingip):
        return self.floatingips_table.get_row(
            self.FLOATING_IPS_TABLE_IP_COLUMN, floatingip)

    @property
    def floatingips_table(self):
        return FloatingIPTable(self.driver)

    def get_floatingip_info(self, floatingip, header):
        row = self._get_row_with_floatingip(floatingip)
        return row.cells[header].text

    def allocate_floatingip(self, pool=None):
        floatingip_form = self.floatingips_table.allocate_ip()
        if pool is not None:
            floatingip_form.pool.text = pool
        floatingip_form.submit()
        ip = re.compile('(([2][5][0-5]\.)|([2][0-4][0-9]\.)'
                        + '|([0-1]?[0-9]?[0-9]\.)){3}(([2][5][0-5])|'
                        '([2][0-4][0-9])|([0-1]?[0-9]?[0-9]))')
        match = ip.search((self._get_element(
            *self._floatingips_fadein_popup_locator)).text)
        floatingip = str(match.group())
        return floatingip

    def release_floatingip(self, floatingip):
        row = self._get_row_with_floatingip(floatingip)
        row.mark()
        confirm_form = self.floatingips_table.release_ip()
        confirm_form.submit()

    def release_floatingip_by_row(self, floatingip):
        row = self._get_row_with_floatingip(floatingip)
        confirm_form = self.floatingips_table.release_ip_by_row(row)
        confirm_form.submit()

    def is_floatingip_present(self, floatingip):
        return bool(self._get_row_with_floatingip(floatingip))

    def associate_floatingip(self, floatingip, instance_name=None,
                             instance_ip=None):
        row = self._get_row_with_floatingip(floatingip)
        floatingip_form = self.floatingips_table.associate_ip(row)
        floatingip_form.instance_id.text = "{}: {}".format(instance_name,
                                                           instance_ip)
        floatingip_form.submit()

    def disassociate_floatingip(self, floatingip):
        row = self._get_row_with_floatingip(floatingip)
        floatingip_form = self.floatingips_table.disassociate_ip(row)
        floatingip_form.submit()

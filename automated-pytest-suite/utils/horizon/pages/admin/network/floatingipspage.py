import re

from utils.horizon.pages.project.network import floatingipspage


class FloatingipsPage(floatingipspage.FloatingipsPage):

    PARTIAL_URL = 'admin/floating_ips'

    def allocate_floatingip(self, pool=None, tenant=None, floating_ip_address=None):
        floatingip_form = self.floatingips_table.allocate_ip()
        if pool is not None:
            floatingip_form.pool.text = pool
        if tenant is not None:
            floatingip_form.tenant.text = tenant
        if floating_ip_address is not None:
            floatingip_form.floating_ip_address.text = floating_ip_address
        floatingip_form.submit()
        ip = re.compile('(([2][5][0-5]\.)|([2][0-4][0-9]\.)'
                        + '|([0-1]?[0-9]?[0-9]\.)){3}(([2][5][0-5])|'
                        '([2][0-4][0-9])|([0-1]?[0-9]?[0-9]))')
        match = ip.search((self._get_element(
            *self._floatingips_fadein_popup_locator)).text)
        floatingip = str(match.group())
        return floatingip
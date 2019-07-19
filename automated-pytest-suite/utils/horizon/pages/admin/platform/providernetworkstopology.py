from selenium.webdriver.common import by
from utils.horizon.pages import basepage
from utils.horizon.helper import HorizonDriver
from utils.horizon.pages.admin.platform.providernetworkoverviewpage import ProvidernetOverviewPage
from utils.horizon.regions import baseregion, tables, forms
from utils import exceptions


class ContainerRegion(baseregion.BaseRegion):
    name = None
    _element_locator = (by.By.CSS_SELECTOR, 'a')
    _text_fluid_locator = (by.By.CSS_SELECTOR, 'detail_view')

    def _container_locator(self, container_name):
        return by.By.CSS_SELECTOR, 'div#%s' % container_name

    def __init__(self, driver, src_element=None):
        if not src_element:
            self._default_src_locator = self._container_locator(self.__class__.name)
            super(ContainerRegion, self).__init__(driver)
        else:
            super(ContainerRegion, self).__init__(driver, src_elem=src_element)

    def select_element_by_name(self, name):
        for element in self._get_elements(*self._element_locator):
            if name == element.text:
                element.click()
                return
            else:
                raise exceptions.HorizonError('{} not found'.format(name))


# class PnetDetail(forms.ItemTextDescription):
#     name = None
#     _detail_view_locator = (by.By.CSS_SELECTOR, 'div#detail_view')
#     _row_fluid_locator = (by.By.CSS_SELECTOR, 'dl > dt')
#     def _container_locator(self, container_name):
#         return by.By.CSS_SELECTOR, 'div#%s' % container_name
#
#     def __init__(self, driver, src_element=None):
#         if not src_element:
#             self._default_src_locator = self._detail_view_locator
#             super(PnetDetail, self).__init__(driver)
#         else:
#             super(PnetDetail, self).__init__(driver, src_elem=src_element)
#
#     def get_detail_view(self):
#         return self._get_element(*self._detail_view_locator)


class ProviderNetworkList(ContainerRegion):
    name = "network_list"


class HostList(ContainerRegion):
    name = "host_list"


class ProviderNetworkDetail(forms.ItemTextDescription):
    _separator_locator = (by.By.CSS_SELECTOR, 'div#info detail')


class ProviderNetworkTopologyPage(basepage.BasePage):

    PARTIAL_URL = 'admin/host_topology'
    # SERVICES_TAB_INDEX = 0
    # USAGE_TAB_INDEX = 1)

    @property
    def host_list(self):
        return HostList(self.driver)

    @property
    def providernet_list(self):
        return ProviderNetworkList(self.driver)

    def providernet_detail(self):
        return ProviderNetworkDetail(self.driver).get_content()

    def go_to_topology_tab(self):
        self.go_to_tab(0)

    def go_to_pnet_overview(self, name):
        link = self._get_element(by.By.LINK_TEXT, name)
        link.click()

        return ProvidernetOverviewPage(HorizonDriver.get_driver(), name)

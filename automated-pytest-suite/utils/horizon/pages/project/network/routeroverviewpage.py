from selenium.webdriver.common import by

from utils.horizon.pages import basepage
from utils.horizon.pages.project.network.networkoverviewpage import NetworkOverviewPage


class RouterOverviewPage(basepage.BasePage):

    _network_link_locator = (by.By.CSS_SELECTOR,
                             'hr+dl.dl-horizontal>dt:nth-child(3)+dd>a')

    def __init__(self, driver, router_name):
        super(RouterOverviewPage, self).__init__(driver)
        self._page_title = router_name

    def is_router_name_present(self, router_name):
        dd_text = self._get_element(by.By.XPATH,
                                    "//dd[.='{0}']".format(router_name)).text
        return dd_text == router_name

    def is_router_status(self, status):
        dd_text = self._get_element(by.By.XPATH,
                                    "//dd[.='{0}']".format(status)).text
        return dd_text == status

    def go_to_router_network(self):
        self._get_element(*self._network_link_locator).click()
        return NetworkOverviewPage(self.driver)

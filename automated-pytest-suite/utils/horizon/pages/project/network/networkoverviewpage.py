from selenium.webdriver.common import by

from utils.horizon.pages import basepage


class NetworkOverviewPage(basepage.BasePage):

    DEFAULT_NETWORK_NAME = 'external-net0'

    def is_network_name_present(self, network_name=DEFAULT_NETWORK_NAME):
        dd_text = self._get_element(by.By.XPATH,
                                    "//dd[.='{0}']".format(network_name)).text
        return dd_text == network_name

    def is_network_status(self, status):
        dd_text = self._get_element(by.By.XPATH,
                                    "//dd[.='{0}']".format(status)).text
        return dd_text == status

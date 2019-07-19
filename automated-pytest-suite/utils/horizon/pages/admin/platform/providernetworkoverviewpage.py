from selenium.webdriver.common import by
from utils.horizon.regions import forms
from utils.horizon.pages import basepage


class ProvidernetOverviewPage(basepage.BasePage):

    def __init__(self, driver, pnet_name):
        super(ProvidernetOverviewPage, self).__init__(driver)
        self._page_title = 'Provider Network Detail: {}'.format(pnet_name)

    def pnet_overview_info_dict(self):
        return forms.ItemTextDescription(self.driver).get_content()

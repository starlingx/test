from utils.horizon.pages import basepage


class OverviewPage(basepage.BasePage):
    def __init__(self, driver):
        super(OverviewPage, self).__init__(driver)
        self._page_title = "Usage Overview"

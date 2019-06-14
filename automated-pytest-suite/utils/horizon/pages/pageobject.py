from utils.horizon import basewebobject
from utils.horizon.helper import HorizonDriver
from consts.proj_vars import ProjVar
from time import sleep


class PageObject(basewebobject.BaseWebObject):
    """Base class for page objects."""
    # BASE_URL = 'http://' + ProjVar.get_var("LAB")['floating ip']
    PARTIAL_URL = None

    def __init__(self, driver=None, port=None):
        if not driver:
            driver = HorizonDriver.get_driver()
        super(PageObject, self).__init__(driver)
        self._page_title = None
        self.port = port

    @property
    def page_title(self):
        return self.driver.title

    @property
    def base_url(self):
        from consts.auth import CliAuth
        prefix = 'http'
        if CliAuth.get_var('HTTPS'):
            prefix = 'https'
        oam_ip = ProjVar.get_var("LAB")['floating ip']

        if not self.port:
            self.port = 8080 if prefix == 'http' else 8443
        base_url = '{}://{}:{}'.format(prefix, oam_ip, self.port)    # horizon url matt
        if not base_url.endswith('/'):
            base_url += '/'
        return base_url

    @property
    def target_url(self):
        return self.base_url + self.PARTIAL_URL

    def get_current_page_url(self):
        return self.driver.current_url

    def close_window(self):
        return self.driver.close()

    def is_nth_window_opened(self, n):
        return len(self.driver.window_handles) == n

    def switch_window(self, window_name=None, window_index=None):
        """Switches focus between the webdriver windows.

        Args:
        - window_name: The name of the window to switch to.
        - window_index: The index of the window handle to switch to.
        If the method is called without arguments it switches to the
         last window in the driver window_handles list.
        In case only one window exists nothing effectively happens.
        Usage:
        page.switch_window('_new')
        page.switch_window(2)
        page.switch_window()
        """

        if window_name is not None and window_index is not None:
            raise ValueError("switch_window receives the window's name or "
                             "the window's index, not both.")
        if window_name is not None:
            self.driver.switch_to.window(window_name)
        elif window_index is not None:
            self.driver.switch_to.window(
                self.driver.window_handles[window_index])
        else:
            self.driver.switch_to.window(self.driver.window_handles[-1])

    def go_to_previous_page(self):
        self.driver.back()

    def go_to_next_page(self):
        self.driver.forward()

    def refresh_page(self):
        self.driver.refresh()

    def go_to_target_page(self):
        self.driver.get(self.target_url)
        sleep(1)

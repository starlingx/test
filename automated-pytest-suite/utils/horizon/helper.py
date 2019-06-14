import contextlib
import tempfile
import os
import time

from selenium import webdriver

try:
    from pyvirtualdisplay import Display
except ImportError:
    Display = None

from consts.proj_vars import ProjVar
from utils.tis_log import LOG


@contextlib.contextmanager
def gen_temporary_file(name='', suffix='.qcow2', size=10485760):
    """Generate temporary file with provided parameters.

    :param name: file name except the extension /suffix
    :param suffix: file extension/suffix
    :param size: size of the file to create, bytes are generated randomly
    :return: path to the generated file
    """
    with tempfile.NamedTemporaryFile(prefix=name, suffix=suffix) as tmp_file:
        tmp_file.write(os.urandom(size))
        yield tmp_file.name


def gen_resource_name(resource="", timestamp=True):
    """Generate random resource name using uuid and timestamp.

    Input fields are usually limited to 255 or 80 characters hence their
    provide enough space for quite long resource names, but it might be
    the case that maximum field length is quite restricted, it is then
    necessary to consider using shorter resource argument or avoid using
    timestamp by setting timestamp argument to False.
    """
    fields = ['test']
    if resource:
        fields.append(resource)
    if timestamp:
        tstamp = time.strftime("%d-%m-%H-%M-%S")
        fields.append(tstamp)
    return "_".join(fields)


class HorizonDriver:
    driver_info = []

    @classmethod
    def get_driver(cls):
        if cls.driver_info:
            return cls.driver_info[0][0]

        LOG.info("Setting Firefox download preferences")
        profile = webdriver.FirefoxProfile()
        # Change default download directory to automation logs dir
        # 2 - download to custom folder
        horizon_dir = ProjVar.get_var('LOG_DIR') + '/horizon'
        os.makedirs(horizon_dir, exist_ok=True)
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.manager.showWhenStarting",
                               False)
        profile.set_preference("browser.download.dir", horizon_dir)
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk",
                               "text/plain,application/x-shellscript")
        # profile.update_preferences()
        display = None
        if Display is not None:
            display = Display(visible=ProjVar.get_var('HORIZON_VISIBLE'),
                              size=(1920, 1080))
            display.start()

        driver_ = webdriver.Firefox(firefox_profile=profile)
        # driver_.maximize_window()
        cls.driver_info.append((driver_, display))
        LOG.info("Web driver created with download preference set")
        return driver_

    @classmethod
    def quit_driver(cls, *driver_display):
        if cls.driver_info:
            driver_, display_ = cls.driver_info[0]
            driver_.quit()
            if display_:
                display_.stop()
            cls.driver_info = []
            profile = webdriver.FirefoxProfile()
            profile.set_preference("browser.download.folderList", 1)
            LOG.info(
                "Quit web driver and reset Firefox download folder to default")

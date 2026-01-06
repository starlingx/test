from optparse import OptionParser

from config.configuration_file_locations_manager import ConfigurationFileLocationsManager
from config.configuration_manager import ConfigurationManager
from framework.resources.resource_finder import get_stx_repo_root
from framework.scanning.objects.test_scanner_uploader import TestScannerUploader

if __name__ == "__main__":
    """
    This Function will scan the repository for all test cases and update the database.

    Usage Example:
        python3 test_case_scanner.py --database_config_file=path/to_my/database_config_file.py

    """

    configuration_locations_manager = ConfigurationFileLocationsManager()
    parser = OptionParser()
    configuration_locations_manager.set_configs_from_options_parser(parser)
    ConfigurationManager.load_configs(configuration_locations_manager)

    repo_root = get_stx_repo_root()
    folders_to_scan = ["testcases"]
    test_scanner_uploader = TestScannerUploader(folders_to_scan)
    test_scanner_uploader.scan_and_upload_tests(repo_root)

from pytest import mark
from keywords.cloud_platform.rest.configuration.system.get_system_keywords import GetSystemKeywords
from config.configuration_manager import ConfigurationManager



@mark.p0
def test_get_system():
    """
    Test to validate get system rest call
    Test Steps:
        - call get system api
        - validate that system mode is equal to the config system mode
    """ 

    system_output = GetSystemKeywords().get_system()
    
    # get lab config for comp purposes
    lab_config = ConfigurationManager.get_lab_config()

    system_object = system_output.get_system_object()

    assert system_object.get_system_mode().lower() == lab_config.get_lab_type().lower()



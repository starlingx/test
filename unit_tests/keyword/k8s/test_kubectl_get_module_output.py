import pytest

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.module.object.kubectl_get_module_output import KubectlGetModuleOutput


def test_init_with_single_module():
    """Test initialization with single module output."""
    output = (
        "NAME              AGE\n",
        "kmm-hello-world   5m\n",
    )
    module_output = KubectlGetModuleOutput(output)
    modules = module_output.get_modules()
    assert len(modules) == 1
    assert modules[0].get_name() == "kmm-hello-world"
    assert modules[0].get_age() == "5m"


def test_init_with_multiple_modules():
    """Test initialization with multiple modules output."""
    output = (
        "NAME              AGE\n",
        "module-1          5m\n",
        "module-2          10m\n",
    )
    module_output = KubectlGetModuleOutput(output)
    modules = module_output.get_modules()
    assert len(modules) == 2
    assert modules[0].get_name() == "module-1"
    assert modules[1].get_name() == "module-2"


def test_get_module_exists():
    """Test getting existing module."""
    output = (
        "NAME              AGE\n",
        "kmm-hello-world   5m\n",
    )
    module_output = KubectlGetModuleOutput(output)
    module = module_output.get_module("kmm-hello-world")
    assert module.get_name() == "kmm-hello-world"


def test_get_module_not_exists():
    """Test getting non-existing module raises exception."""
    output = (
        "NAME              AGE\n",
        "kmm-hello-world   5m\n",
    )
    module_output = KubectlGetModuleOutput(output)
    with pytest.raises(KeywordException, match="There is no module with the name"):
        module_output.get_module("non-existing")


def test_module_exists_true():
    """Test module_exists returns True for existing module."""
    output = (
        "NAME              AGE\n",
        "kmm-hello-world   5m\n",
    )
    module_output = KubectlGetModuleOutput(output)
    assert module_output.module_exists("kmm-hello-world") is True


def test_module_exists_false():
    """Test module_exists returns False for non-existing module."""
    output = (
        "NAME              AGE\n",
        "kmm-hello-world   5m\n",
    )
    module_output = KubectlGetModuleOutput(output)
    assert module_output.module_exists("non-existing") is False

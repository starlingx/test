"""Unit tests for the O2 IMS inventory Output parsers.

Builds each typed Output from a synthetic response carrying canned JSON and
asserts the getters. Lab-free: no SSH, no live system. Mirrors the
canned-input, no-lab style of the other parser unit tests.

Only the fields the assertions read are modelled; fields such as
`extensions`, `supportedLocations` and `alarmDictionary` are intentionally not
modelled and not asserted.
"""

from keywords.cloud_platform.rest.oran_o2.object.o2_api_versions_output import O2ApiVersionsOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_deployment_managers_output import O2DeploymentManagersOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_ocloud_root_output import O2OcloudRootOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_resource_pools_output import O2ResourcePoolsOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_resource_types_output import O2ResourceTypesOutput
from keywords.cloud_platform.rest.oran_o2.object.o2_resources_output import O2ResourcesOutput


class FakeO2RestResponse:
    """Minimal stand-in for O2RestResponse that returns pre-parsed JSON content."""

    def __init__(self, content: dict | list):
        """Store the pre-parsed content.

        Args:
            content (dict | list): The JSON content the Output should parse.
        """
        self.content = content

    def get_json_content(self) -> dict | list:
        """Return the pre-parsed JSON content.

        Returns:
            dict | list: The stored content.
        """
        return self.content


def test_api_versions_output_extracts_versions():
    """api_versions Output extracts the version strings under apiVersions."""
    response = FakeO2RestResponse({"uriPrefix": "x", "apiVersions": [{"version": "1.0.0"}, {"version": "2.0.0"}]})
    output = O2ApiVersionsOutput(response)
    assert output.is_empty() is False
    assert output.get_versions() == ["1.0.0", "2.0.0"]


def test_api_versions_output_empty():
    """api_versions Output reports empty when no versions are present."""
    output = O2ApiVersionsOutput(FakeO2RestResponse({"apiVersions": []}))
    assert output.is_empty() is True
    assert output.get_versions() == []


def test_ocloud_root_output_ids():
    """O-Cloud root Output exposes oCloudId and globalcloudId presence."""
    response = FakeO2RestResponse({"oCloudId": "oc-1", "globalcloudId": "", "name": "lab"})
    output = O2OcloudRootOutput(response)
    assert output.get_ocloud_id() == "oc-1"
    assert output.has_global_cloud_id() is True
    assert output.get_global_cloud_id() == ""


def test_ocloud_root_output_missing_global_cloud_id():
    """O-Cloud root Output reports globalcloudId absent when the key is missing."""
    output = O2OcloudRootOutput(FakeO2RestResponse({"oCloudId": "oc-1"}))
    assert output.has_global_cloud_id() is False


def test_resource_types_output_parses_ids():
    """resourceTypes Output parses each resourceTypeId and navigates."""
    response = FakeO2RestResponse([{"resourceTypeId": "rt-1"}, {"resourceTypeId": "rt-2"}])
    output = O2ResourceTypesOutput(response)
    assert output.is_empty() is False
    assert [rt.get_resource_type_id() for rt in output.get_resource_types()] == ["rt-1", "rt-2"]
    assert output.get_first().get_resource_type_id() == "rt-1"


def test_resource_pools_output_parses_ids():
    """resourcePools Output parses each resourcePoolId and navigates."""
    response = FakeO2RestResponse([{"resourcePoolId": "rp-1"}])
    output = O2ResourcePoolsOutput(response)
    assert output.is_empty() is False
    assert output.get_first().get_resource_pool_id() == "rp-1"


def test_resources_output_parses_ids():
    """resources Output parses each resourceId and navigates."""
    response = FakeO2RestResponse([{"resourceId": "r-1"}, {"resourceId": "r-2"}])
    output = O2ResourcesOutput(response)
    assert output.is_empty() is False
    assert output.get_first().get_resource_id() == "r-1"


def test_deployment_managers_output_parses_ids():
    """deploymentManagers Output parses each deploymentManagerId and navigates."""
    response = FakeO2RestResponse([{"deploymentManagerId": "dm-1"}])
    output = O2DeploymentManagersOutput(response)
    assert output.is_empty() is False
    assert output.get_first().get_deployment_manager_id() == "dm-1"


def test_resource_types_output_parses_detail_response():
    """A detail read returning one object parses as a single-entry Output."""
    output = O2ResourceTypesOutput(FakeO2RestResponse({"resourceTypeId": "rt-1", "name": "pserver"}))
    assert output.is_empty() is False
    assert len(output.get_resource_types()) == 1
    assert output.get_first().get_resource_type_id() == "rt-1"


def test_resource_pools_output_parses_detail_response():
    """A detail read returning one object parses as a single-entry Output."""
    output = O2ResourcePoolsOutput(FakeO2RestResponse({"resourcePoolId": "rp-1", "name": "pool"}))
    assert output.is_empty() is False
    assert len(output.get_resource_pools()) == 1
    assert output.get_first().get_resource_pool_id() == "rp-1"


def test_resources_output_parses_detail_response():
    """A detail read returning one object parses as a single-entry Output."""
    output = O2ResourcesOutput(FakeO2RestResponse({"resourceId": "r-1", "resourcePoolId": "rp-1"}))
    assert output.is_empty() is False
    assert len(output.get_resources()) == 1
    assert output.get_first().get_resource_id() == "r-1"


def test_deployment_managers_output_parses_detail_response():
    """A detail read returning one object parses as a single-entry Output."""
    output = O2DeploymentManagersOutput(FakeO2RestResponse({"deploymentManagerId": "dm-1", "name": "dm"}))
    assert output.is_empty() is False
    assert len(output.get_deployment_managers()) == 1
    assert output.get_first().get_deployment_manager_id() == "dm-1"


def test_collection_output_ignores_detail_response_without_id():
    """A detail-shaped response with no id yields an empty Output rather than raising."""
    output = O2ResourcePoolsOutput(FakeO2RestResponse({"name": "pool", "description": "no id"}))
    assert output.is_empty() is True

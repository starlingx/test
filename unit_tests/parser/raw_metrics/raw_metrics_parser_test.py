from keywords.k8s.raw_metrics.object.kubectl_get_raw_metrics_output import KubectlGetRawMetricsOutput

default_deprecated_apis = [
    'apiserver_requested_deprecated_apis{group="cdi.kubevirt.io",removed_release="",resource="objecttransfers",subresource="",version="v1beta1"} 1\n',
    'apiserver_requested_deprecated_apis{group="helm.toolkit.fluxcd.io",removed_release="",resource="helmreleases",subresource="",version="v2beta1"} 1\n',
]


def test_raw_metrics_output():
    """
    Test all methods in KubectlGetRawMetricsOutput class.
    """
    deprecated_api_default = KubectlGetRawMetricsOutput(default_deprecated_apis)
    deprecated_api_default_obj_list = deprecated_api_default.get_raw_metrics()
    for deprecated_api_default_obj in deprecated_api_default_obj_list:
        assert deprecated_api_default_obj.get_metric() == "apiserver_requested_deprecated_apis"
        assert deprecated_api_default_obj.get_labels() == {"group": "cdi.kubevirt.io", "removed_release": "", "resource": "objecttransfers", "subresource": "", "version": "v1beta1"} or {"group": "helm.toolkit.fluxcd.io", "removed_release": "", "resource": "helmreleases", "subresource": "", "version": "v2beta1"}
        assert deprecated_api_default_obj.get_value() == "1"

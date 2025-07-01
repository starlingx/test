import re

from keywords.k8s.raw_metrics.object.kubectl_raw_metric_object import KubectlRawMetricObject


class KubectlGetRawMetricsOutput:
    """
    Class to parse the output from the `kubectl get --raw /metrics` command.

    This class processes the raw metrics output, extracting metric names, labels, and values,
    and stores them in instances of `KubectlRawMetricObject`.
    """

    def __init__(self, kubectl_get_raw_metrics_output: str):
        """
        Initializes the object by parsing the output from the `kubectl get --raw /metrics` command.

        Parses each line of the provided output, extracting metric names, labels, and values, and stores them as
        instances of `KubectlRawMetricObject` in the `kubectl_raw_metrics` list. Lines that are empty or start with
        a '#' character are ignored.
        the regex pattern matches lines in the format:
        metric_name{label1="value1", label2="value2"} value
        example: "apiserver_requested_deprecated_apis{group="helm.toolkit.fluxcd.io"} 1

        Args:
            kubectl_get_raw_metrics_output (str): The raw string output from the kubectl metrics command.

        """
        pattern = re.compile(r"^(?P<metric>\w+)\{(?P<labels>[^}]*)\}\s+(?P<value>.+)$")
        self.kubectl_raw_metrics: [KubectlRawMetricObject] = []
        for line in kubectl_get_raw_metrics_output:
            if not line or line.startswith("#"):
                continue
            match = pattern.match(line)
            if match:
                raw_metric = KubectlRawMetricObject()
                metric = match.group("metric")
                raw_metric.set_metric(metric)
                labels = dict(item.split("=") for item in match.group("labels").split(",") if "=" in item)
                labels = {k: v.strip('"') for k, v in labels.items()}
                raw_metric.set_labels(labels)

                value = match.group("value")
                raw_metric.set_value(value)

                self.kubectl_raw_metrics.append(raw_metric)

    def get_raw_metrics(self) -> list[KubectlRawMetricObject]:
        """
        Return parsed raw metrics objects.

        Returns:
            list[KubectlRawMetricObject]: List of parsed raw metrics objects.
        """
        return self.kubectl_raw_metrics

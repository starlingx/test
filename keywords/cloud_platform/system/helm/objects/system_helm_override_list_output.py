import re
from typing import List

from keywords.cloud_platform.system.helm.objects.system_helm_override_chart_object import HelmOverrideChartObject
from keywords.cloud_platform.system.system_table_parser import SystemTableParser


class SystemHelmOverrideListOutput:
    """
    This class parses the output of 'system helm-override-list <app>' into a list of HelmOverrideChartObject.

    Example of the output:
    +------------+----------------------+
    | chart name | overrides namespaces |
    +------------+----------------------+
    | aodh       | ['openstack']        |
    | nova       | ['openstack']        |
    +------------+----------------------+
    """

    def __init__(self, helm_override_list_output: str):
        """
        Constructor

        Args:
            helm_override_list_output (str): Output of the 'system helm-override-list <app>' command.
        """
        self.charts: List[HelmOverrideChartObject] = []
        for row in SystemTableParser(helm_override_list_output).get_output_values_list():
            # The columns are read by position: when the table wraps the header over two
            # lines, the parser joins it without a space ("overridesnamespaces").
            chart_name, namespaces_cell = list(row.values())[:2]
            namespaces = re.findall(r"[A-Za-z0-9_.-]+", namespaces_cell)
            self.charts.append(HelmOverrideChartObject(chart_name.strip(), namespaces))

    def get_charts(self) -> List[HelmOverrideChartObject]:
        """
        Get the charts of the application.

        Returns:
            List[HelmOverrideChartObject]: One object per chart, with its override namespaces.
        """
        return self.charts

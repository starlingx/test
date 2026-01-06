from typing import Union

from framework.exceptions.keyword_exception import KeywordException
from keywords.k8s.helm.object.kubectl_helm_object import KubectlHelmObject


class KubectlGetHelmOutput:
    """Parser for 'kubectl get helmcharts' command output."""

    def __init__(self, kubectl_output: Union[str, list[str]]):
        """Initialize KubectlGetHelmOutput.

        Args:
            kubectl_output (Union[str, list[str]]): Raw kubectl get helmcharts output.
        """
        self.helms = self._parse_output(kubectl_output)

    def _parse_output(self, output: Union[str, list[str]]) -> list[KubectlHelmObject]:
        """Parse kubectl get helmcharts output into helm objects.

        Args:
            output (Union[str, list[str]]): Raw command output.

        Returns:
            list[KubectlHelmObject]: List of parsed helm objects.
        """
        helms = []
        content = "\n".join(output) if isinstance(output, list) else output
        lines = content.strip().split("\n")

        if len(lines) < 2:
            return helms

        # Skip header line
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    name = parts[0]
                    chart = parts[1]
                    version = parts[2]

                    helm = KubectlHelmObject(name)
                    helm.set_chart(chart)
                    helm.set_version(version)
                    helms.append(helm)

        return helms

    def get_helmcharts(self) -> list[KubectlHelmObject]:
        """Get all helms.

        Returns:
            list[KubectlHelmObject]: List of all helms.
        """
        return self.helms

    def get_helmchart(self, name: str) -> KubectlHelmObject:
        """Get specific helm by name.

        Args:
            name (str): Name of the helm.

        Returns:
            KubectlHelmObject: The helm object.

        Raises:
            KeywordException: If helm not found.
        """
        for helm in self.helms:
            if helm.get_name() == name:
                return helm
        raise KeywordException(f"Helm {name} not found")

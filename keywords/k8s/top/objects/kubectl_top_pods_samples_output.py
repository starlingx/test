"""Output object for a series of 'kubectl top pods' readings."""

from keywords.k8s.top.objects.kubectl_top_output import KubectlTopOutput


class KubectlTopPodsSamplesOutput:
    """Per-pod CPU and memory series built from several 'kubectl top pods' readings.

    Each sample is the set of readings taken at the same time across one or more
    namespaces.
    """

    def __init__(self, samples: list[list[KubectlTopOutput]]):
        """Build the per-pod series from the readings.

        Args:
            samples (list[list[KubectlTopOutput]]): One list of readings per sample, one reading per namespace.
        """
        self.sample_count = len(samples)
        self.cpu_millicores: dict[str, list[int]] = {}
        self.memory_mebibytes: dict[str, list[int]] = {}
        for sample in samples:
            for reading in sample:
                for entry in reading.get_entries():
                    self.cpu_millicores.setdefault(entry.get_name(), []).append(entry.get_cpu_millicores())
                    self.memory_mebibytes.setdefault(entry.get_name(), []).append(entry.get_memory_mebibytes())

    def get_sample_count(self) -> int:
        """Get the number of samples taken.

        Returns:
            int: The number of samples.
        """
        return self.sample_count

    def get_pod_names(self) -> list[str]:
        """Get the pods that appear in at least one sample.

        Returns:
            list[str]: The pod names, sorted.
        """
        return sorted(self.cpu_millicores.keys())

    def get_pods_missing_samples(self) -> list[str]:
        """Get the pods that are absent from at least one sample, for example after a restart.

        Returns:
            list[str]: Pod names with their sample count, for pods with fewer samples than were taken.
        """
        return [f"{pod_name}: {len(values)}/{self.sample_count} samples" for pod_name, values in sorted(self.cpu_millicores.items()) if len(values) != self.sample_count]

    def get_cpu_millicores(self, pod_name: str) -> list[int]:
        """Get the CPU readings of a pod.

        Args:
            pod_name (str): The pod name.

        Returns:
            list[int]: The CPU readings in millicores, in sample order.

        Raises:
            ValueError: If the pod does not appear in any sample.
        """
        if pod_name not in self.cpu_millicores:
            raise ValueError(f"Pod {pod_name} does not appear in any 'kubectl top pods' sample")
        return self.cpu_millicores[pod_name]

    def get_memory_mebibytes(self, pod_name: str) -> list[int]:
        """Get the memory readings of a pod.

        Args:
            pod_name (str): The pod name.

        Returns:
            list[int]: The memory readings in Mi, in sample order.

        Raises:
            ValueError: If the pod does not appear in any sample.
        """
        if pod_name not in self.memory_mebibytes:
            raise ValueError(f"Pod {pod_name} does not appear in any 'kubectl top pods' sample")
        return self.memory_mebibytes[pod_name]

    def __str__(self) -> str:
        """Human-readable representation of the samples.

        Returns:
            str: The sample count and the sampled pods.
        """
        return f"KubectlTopPodsSamplesOutput(samples={self.sample_count}, pods={self.get_pod_names()})"

"""Unit tests for the Kubernetes quantity converter."""

import unittest

from keywords.k8s.k8s_quantity_converter import K8sQuantityConverter


class K8sQuantityConverterTest(unittest.TestCase):
    """Exercise the CPU and memory quantity conversions."""

    def setUp(self) -> None:
        """Build the converter once per test."""
        self.converter = K8sQuantityConverter()

    def test_cpu_quantity_to_millicpu(self) -> None:
        """Milli, whole and fractional CPU quantities convert to millicpu."""
        self.assertEqual(self.converter.cpu_quantity_to_millicpu("200m"), 200)
        self.assertEqual(self.converter.cpu_quantity_to_millicpu("2"), 2000)
        self.assertEqual(self.converter.cpu_quantity_to_millicpu("0.5"), 500)

    def test_cpu_limit_to_quota(self) -> None:
        """A CPU limit converts to a CFS quota for the given period, including a non-default one."""
        self.assertEqual(self.converter.cpu_limit_to_quota("200m", 100000), 20000)
        self.assertEqual(self.converter.cpu_limit_to_quota("1", 100000), 100000)
        self.assertEqual(self.converter.cpu_limit_to_quota("500m", 50000), 25000)
        self.assertEqual(self.converter.cpu_limit_to_quota("200m", 50000), 10000)

    def test_memory_quantity_to_bytes(self) -> None:
        """Binary, decimal and plain-byte memory quantities convert to bytes."""
        self.assertEqual(self.converter.memory_quantity_to_bytes("128Mi"), 134217728)
        self.assertEqual(self.converter.memory_quantity_to_bytes("1Gi"), 1073741824)
        self.assertEqual(self.converter.memory_quantity_to_bytes("64M"), 64000000)
        self.assertEqual(self.converter.memory_quantity_to_bytes("1073741824"), 1073741824)


if __name__ == "__main__":
    unittest.main()

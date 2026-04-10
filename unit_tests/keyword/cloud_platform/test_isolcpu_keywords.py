"""
Unit tests for parse_cpu_range method in CpuManagerStateObject.
"""

import unittest

from keywords.k8s.cat.object.cpu_manager_state_object import CpuManagerStateObject


class TestParseCpuRange(unittest.TestCase):
    """
    Test suite for CpuManagerStateObject.parse_cpu_range.
    """

    def setUp(self):
        """
        Set up test fixture with CpuManagerStateObject instance.
        """
        self.state_obj = CpuManagerStateObject()

    def test_single_cpu(self):
        """
        Test parsing a single CPU ID.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("5"), [5])

    def test_cpu_range(self):
        """
        Test parsing a contiguous CPU range.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0-3"), [0, 1, 2, 3])

    def test_comma_separated_cpus(self):
        """
        Test parsing comma-separated individual CPU IDs.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0,2,4"), [0, 2, 4])

    def test_mixed_range_and_individual(self):
        """
        Test parsing a mix of ranges and individual CPU IDs.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0-3,5,7-9"), [0, 1, 2, 3, 5, 7, 8, 9])

    def test_single_element_range(self):
        """
        Test parsing a range where start equals end.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("4-4"), [4])

    def test_empty_string(self):
        """
        Test parsing an empty string returns empty list.
        """
        self.assertEqual(self.state_obj.parse_cpu_range(""), [])

    def test_whitespace_around_parts(self):
        """
        Test parsing CPU string with spaces around commas.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0, 2, 4"), [0, 2, 4])

    def test_zero_cpu(self):
        """
        Test parsing CPU ID zero.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0"), [0])

    def test_large_range(self):
        """
        Test parsing a large CPU range.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0-7"), [0, 1, 2, 3, 4, 5, 6, 7])

    def test_multiple_ranges(self):
        """
        Test parsing multiple non-contiguous ranges.
        """
        self.assertEqual(self.state_obj.parse_cpu_range("0-1,4-5"), [0, 1, 4, 5])

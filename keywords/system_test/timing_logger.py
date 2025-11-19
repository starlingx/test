import csv
import os
from datetime import datetime
from typing import Dict, List

from framework.validation.validation import validate_equals

# Default directory for saving benchmark timing logs
DEFAULT_BENCHMARK_LOG_DIR = "benchmark_results"

# HTML template for benchmark results
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
        .metric {{ font-weight: bold; text-align: left; }}
    </style>
</head>
<body>
    <h2>{title}</h2>
    <table>
        <thead>
            <tr>
                <th class="metric">Metric</th>
                {iteration_headers}
                <th>Average</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</body>
</html>
"""


class TimingLogger:
    """
    Utility class to log system test benchmark timings to HTML and CSV files.

    This class provides functionality to record timing measurements for benchmark tests
    and generate both CSV and HTML reports with statistical summaries.

    Attributes:
        benchmark_type (str): Type/name of the benchmark being measured
        output_dir (str): Directory where output files will be saved
        csv_file (str): Full path to the CSV output file
        html_file (str): Full path to the HTML output file

    Example:
        >>> logger = TimingLogger("container_deployment")
        >>> logger.log_timings(45.2, 12.8, 8.5)
    """

    def __init__(self, benchmark_type: str, output_dir: str = DEFAULT_BENCHMARK_LOG_DIR, column_headers: List[str] = None):
        """
        Initialize the TimingLogger.

        Args:
            benchmark_type (str): Name/type of benchmark (used in filenames)
            output_dir (str, optional): Directory to save files. Defaults to DEFAULT_BENCHMARK_LOG_DIR.
            column_headers (List[str], optional): Custom column headers. Defaults to ['Deploy Time (s)', 'Scale Up Time (s)', 'Scale Down Time (s)'].

        Creates:
            - Output directory if it doesn't exist
            - CSV file path: {output_dir}/{benchmark_type}_benchmark_timings.csv
            - HTML file path: {output_dir}/{benchmark_type}_benchmark_timings.html
        """
        self.benchmark_type = benchmark_type
        self.output_dir = output_dir
        self.csv_file = os.path.join(output_dir, f"{benchmark_type}_benchmark_timings.csv")
        self.html_file = os.path.join(output_dir, f"{benchmark_type}_benchmark_timings.html")
        self.column_headers = column_headers or ['Deploy Time (s)', 'Scale Up Time (s)', 'Scale Down Time (s)']

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

    def log_timings(self, *timing_values: float):
        """
        Log timing measurements to both CSV and HTML files.

        Args:
            *timing_values (float): Variable number of timing values in seconds

        This method appends the timing data to the CSV file and regenerates
        the HTML report with updated statistics including averages.
        """
        validate_equals(len(timing_values), len(self.column_headers), 
                        f"Expected {len(self.column_headers)}, got {len(timing_values)}")
        self._log_to_csv(*timing_values)
        self._generate_html_table()

    def _log_to_csv(self, *timing_values: float):
        """
        Append timing data to CSV file with timestamp.

        Args:
            *timing_values (float): Variable number of timing values in seconds

        Creates CSV header if file doesn't exist. Each row contains:
        timestamp, timing_value1, timing_value2, ...
        """
        file_exists = os.path.exists(self.csv_file)

        with open(self.csv_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)

            if not file_exists:
                writer.writerow(['Timestamp'] + self.column_headers)

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            formatted_values = [f"{value:.2f}" for value in timing_values]
            writer.writerow([timestamp] + formatted_values)

    def _read_csv_data(self) -> List[Dict]:
        """
        Read existing CSV data into a list of dictionaries.

        Returns:
            List[Dict]: List of timing records, each as a dictionary with keys:
                       'Timestamp', 'Deploy Time (s)', 'Scale Up Time (s)', 'Scale Down Time (s)'
                       Returns empty list if CSV file doesn't exist.
        """
        data = []
        if os.path.exists(self.csv_file):
            with open(self.csv_file, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                data = list(reader)
        return data

    def _calculate_averages(self, data: List[Dict]) -> Dict[str, float]:
        """
        Calculate average timing values from CSV data.

        Args:
            data (List[Dict]): List of timing records from CSV

        Returns:
            Dict[str, float]: Dictionary with column headers as keys containing average times.
        """
        if not data:
            return {header: 0.0 for header in self.column_headers}

        avg_timings = {}
        for header in self.column_headers:
            values = [float(row[header]) for row in data]
            avg_timings[header] = sum(values) / len(values)

        return avg_timings

    def _generate_html_table(self):
        """
        Generate HTML report from CSV data using template.

        Creates an HTML file with a table showing all timing iterations
        and calculated averages.
        """
        data = self._read_csv_data()
        averages = self._calculate_averages(data)

        # Generate iteration headers
        iteration_headers = "".join(f"<th>Iteration {i+1}</th>" for i in range(len(data)))

        # Generate table rows
        table_rows = []
        for header in self.column_headers:
            row_cells = [f'<td class="metric">{header}</td>']
            row_cells.extend(f"<td>{row[header]}</td>" for row in data)
            row_cells.append(f"<td><strong>{averages[header]:.2f}</strong></td>")
            table_rows.append(f"<tr>{''.join(row_cells)}</tr>")

        # Format HTML using template
        html_content = HTML_TEMPLATE.format(
            title=f"{self.benchmark_type.title()} Benchmark Results",
            iteration_headers=iteration_headers,
            table_rows="".join(table_rows)
        )

        with open(self.html_file, 'w') as htmlfile:
            htmlfile.write(html_content)
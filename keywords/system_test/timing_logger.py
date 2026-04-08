import csv
import os
from datetime import datetime
from typing import Dict, List

from framework.logging.automation_logger import get_logger
from framework.validation.validation import validate_equals

# Default directory for saving benchmark timing logs
DEFAULT_BENCHMARK_LOG_DIR = "benchmark_results"


HTML_REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ color: #333; }}
        .timestamp {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        .step {{ font-weight: bold; }}
        .step-indent {{ padding-left: 30px; }}
        .stage-row {{ background-color: #d9e8f5; }}
        .stage-row td {{ font-weight: bold; font-size: 14px; }}
        .total-row {{ background-color: #e8f4f8; }}
        .total-row td {{ font-weight: bold; }}
        .stats-cell {{ background-color: #fff3cd; }}
    </style>
</head>
<body>
    <h2>{title}</h2>
    <div class="timestamp">Generated: {timestamp}</div>
    <table>
        <thead>
            <tr>
                <th>Stage / Step Name</th>
                {header_cols}
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</body>
</html>
"""

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


class PatchingTimingLogger:
    """
    Timing logger specifically for patching operations.

    Creates HTML, CSV, and raw text reports for patch apply and remove operations.
    """

    def __init__(self, output_dir: str = DEFAULT_BENCHMARK_LOG_DIR):
        """
        Initialize the PatchingTimingLogger.

        Args:
            output_dir (str): Directory to save timing reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.execution_counter = self._get_next_execution_number()

    def _get_next_execution_number(self) -> int:
        """
        Get the next execution number by checking existing files.

        Returns:
            int: Next execution number
        """
        existing_files = [f for f in os.listdir(self.output_dir) if f.startswith("patch_") and f.endswith(".txt")]
        if not existing_files:
            return 1

        max_num = 0
        for filename in existing_files:
            try:
                parts = filename.split("_exec_")
                if len(parts) == 2:
                    num = int(parts[1].split(".")[0])
                    max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue

        return max_num + 1

    def save_raw_output(self, operation_type: str, raw_output: List[str]):
        """
        Save raw sw-deploy-strategy show --details output to text file.

        Args:
            operation_type (str): Either "apply" or "remove"
            raw_output (List[str]): Raw command output lines
        """
        txt_file = os.path.join(self.output_dir, f"patch_{operation_type}_exec_{self.execution_counter}.txt")
        with open(txt_file, 'w') as f:
            f.write("\n".join(raw_output))

    def log_patch_timings(self, operation_type: str, stages: List[Dict[str, any]]):
        """
        Log patch timing measurements to HTML and CSV files.

        Args:
            operation_type (str): Either "apply" or "remove"
            stages (List[Dict]): Stage and step timing data
        """
        total_steps = sum(len(stage['steps']) for stage in stages)
        total_duration = sum(step['duration'] for stage in stages for step in stage['steps'])

        get_logger().log_info(f"Patch {operation_type} completed with {len(stages)} stages and {total_steps} steps")
        get_logger().log_info(f"Total patch {operation_type} duration: {self._format_duration(total_duration)}")

        html_file = os.path.join(self.output_dir, f"patching_{operation_type}_timings.html")
        csv_file = os.path.join(self.output_dir, f"patching_{operation_type}_timings.csv")
        self._generate_csv_report(csv_file, stages, total_duration)
        self._generate_html_report(html_file, operation_type, stages, total_duration)

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to hh:mm:ss format.

        Args:
            seconds (float): Duration in seconds

        Returns:
            str: Formatted duration string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _generate_csv_report(self, csv_file: str, stages: List[Dict[str, any]], total_duration: float):
        """
        Generate CSV report with hierarchical stage and step timing details.

        Args:
            csv_file (str): Path to CSV file
            stages (List[Dict]): Stage and step timing data
            total_duration (float): Total duration in seconds
        """
        existing_data = self._read_existing_csv_data(csv_file) if os.path.exists(csv_file) else {}
        existing_rows = existing_data.get('rows', {})
        existing_totals = existing_data.get('totals', [])
        iteration_num = len(existing_totals) + 1

        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Stage / Step Name"] + [f"Iteration {i}" for i in range(1, iteration_num + 1)] + ["min/max/average"])

            for stage in stages:
                stage_name = f"Stage: {stage['stage_name']}"
                writer.writerow([stage_name] + existing_rows.get(stage_name, [""] * (iteration_num - 1)) + [""])

                for step in stage['steps']:
                    step_name = f"  {step['step_name']}"
                    existing_values = existing_rows.get(step_name, [""] * (iteration_num - 1))
                    writer.writerow([step_name] + existing_values + [self._format_duration(step['duration'])])

            all_totals = existing_totals + [total_duration]
            stats = f"{self._format_duration(min(all_totals))} / {self._format_duration(max(all_totals))} / {self._format_duration(sum(all_totals) / len(all_totals))}"
            writer.writerow(["TOTAL"] + [self._format_duration(t) for t in all_totals] + [stats])

    def _read_existing_csv_data(self, csv_file: str) -> Dict:
        """
        Read existing CSV file to extract all previous iteration data.

        Args:
            csv_file (str): Path to CSV file

        Returns:
            Dict: Dictionary with rows and totals data
        """
        try:
            with open(csv_file, 'r') as f:
                rows_list = list(csv.reader(f))

            if not rows_list:
                return {}

            num_iterations = len([col for col in rows_list[0] if col.startswith("Iteration")])
            rows_data = {}
            totals = []

            for row in rows_list[1:]:
                if not row:
                    continue

                if row[0] == "TOTAL":
                    totals = [self._parse_duration(row[i]) for i in range(1, num_iterations + 1) if i < len(row) and row[i]]
                else:
                    rows_data[row[0]] = [row[i] if i < len(row) else "" for i in range(1, num_iterations + 1)]

            return {'rows': rows_data, 'totals': totals}
        except Exception:
            return {}

    def _parse_duration(self, duration_str: str) -> float:
        """
        Parse duration string in hh:mm:ss format to seconds.

        Args:
            duration_str (str): Duration in hh:mm:ss format

        Returns:
            float: Duration in seconds
        """
        parts = duration_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours * 3600 + minutes * 60 + seconds

    def _read_existing_csv_for_html(self, csv_file: str) -> Dict:
        """
        Read existing CSV file to extract all previous iteration data for HTML generation.

        Args:
            csv_file (str): Path to CSV file

        Returns:
            Dict: Dictionary with rows and totals data
        """
        try:
            with open(csv_file, 'r') as f:
                rows_list = list(csv.reader(f))

            if not rows_list:
                return {'rows': {}, 'totals': [], 'num_iterations': 0}

            num_iterations = len([col for col in rows_list[0] if col.startswith("Iteration")])
            rows_data = {}
            totals = []

            for row in rows_list[1:]:
                if not row:
                    continue

                if row[0] == "TOTAL":
                    totals = [self._parse_duration(row[i]) for i in range(1, num_iterations + 1) if i < len(row) and row[i]]
                elif row[0].startswith("  "):  # Step row
                    step_name = row[0].strip()
                    rows_data[step_name] = [row[i] if i < len(row) and row[i] else "" for i in range(1, num_iterations + 1)]

            return {'rows': rows_data, 'totals': totals, 'num_iterations': num_iterations}
        except Exception:
            return {'rows': {}, 'totals': [], 'num_iterations': 0}

    def _generate_html_report(self, html_file: str, operation_type: str, stages: List[Dict[str, any]], total_duration: float):
        """
        Generate HTML report with hierarchical stage and step timing details.

        Args:
            html_file (str): Path to HTML file
            operation_type (str): Operation type for title
            stages (List[Dict]): Stage and step timing data
            total_duration (float): Total duration in seconds
        """
        html_content = self._build_html_content(operation_type, stages, total_duration)

        with open(html_file, 'w') as htmlfile:
            htmlfile.write(html_content)

    def _build_html_content(self, operation_type: str, stages: List[Dict[str, any]], total_duration: float) -> str:
        """
        Build HTML content for the report with hierarchical stage and step structure.

        Args:
            operation_type (str): Operation type for title
            stages (List[Dict]): Stage and step timing data
            total_duration (float): Total duration in seconds

        Returns:
            str: HTML content
        """
        csv_file = os.path.join(self.output_dir, f"patching_{operation_type}_timings.csv")
        existing_data = self._read_existing_csv_for_html(csv_file) if os.path.exists(csv_file) else {'rows': {}, 'totals': [], 'num_iterations': 0}
        existing_rows = existing_data.get('rows', {})
        existing_totals = existing_data.get('totals', [])
        num_iterations = existing_data.get('num_iterations', 0)

        header_cols = "".join([f"<th>Iteration {i}</th>" for i in range(1, num_iterations + 1)]) + "<th>min/max/average</th>"

        table_rows = ""
        for stage in stages:
            table_rows += f'<tr class="stage-row"><td colspan="{num_iterations + 2}"><strong>Stage: {stage["stage_name"]}</strong></td></tr>'

            for step in stage['steps']:
                step_name = step['step_name']
                existing_values = existing_rows.get(step_name, [])
                row_cols = "".join([f"<td><strong>{val}</strong></td>" for val in existing_values])
                row_cols += "<td></td>"  # Empty Statistics column for step rows
                table_rows += f'<tr><td class="step-indent">{step_name}</td>{row_cols}</tr>'

        total_cols = "".join([f"<td><strong>{self._format_duration(t)}</strong></td>" for t in existing_totals])
        stats = f"{self._format_duration(min(existing_totals))} / {self._format_duration(max(existing_totals))} / {self._format_duration(sum(existing_totals) / len(existing_totals))}"
        table_rows += f'<tr class="total-row"><td class="step"><strong>TOTAL</strong></td>{total_cols}<td class="stats-cell"><strong>{stats}</strong></td></tr>'

        return HTML_REPORT_TEMPLATE.format(
            title=f"Patching {operation_type.title()} Timing Results",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            header_cols=header_cols,
            table_rows=table_rows
        )

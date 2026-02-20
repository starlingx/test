from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import re
import csv
import gzip
import os

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword
from tabulate import tabulate

class LogPatternKpiKeywords(BaseKeyword):
    """
    Log Pattern Matching Profiler (LPMP) engine for KPI calculation.
    
    This class provides the core engine for pattern matching and timing analysis.
    Block definitions should be provided from separate configuration files.
    
    Features:
    - Sequential mode: Process patterns in order with queuing
    - Pair mode: Measure start/stop pattern timing with validation
    - File position tracking and chronological ordering
    - Wildcard expansion and compressed file handling
    - Variable substitution and OR patterns
    - max_time_delta validation for timing constraints
    - Optional blocks and model info extraction
    """

    def __init__(self, ssh_connection: SSHConnection):
        """Initialize with SSH connection.
        
        Args:
            ssh_connection (SSHConnection): SSH connection to remote host
        """
        self.ssh_connection = ssh_connection

    def calculate_kpi(self, hostname: str, blocks: List[Dict[str, Any]], 
                            start_date: Optional[str] = None, loops: int = 1,
                            max_log_length: int = 180, time_tolerance: float = 1.0,
                            output_file: str = "profile.timing",
                            csv_file: str = "profile.csv",
                            logs_dir: str = "/var/log",
                            verbose: bool = True,
                            pair_mode: bool = False,
                            max_time_delta: float = 500.0) -> Tuple[List[str], List[List]]:
        """
        Calculate unlock KPI timing - main entry point.

        Args:
            hostname (str): Hostname for {hostname} substitution
            blocks (List[Dict]): Block definitions (patterns or start/stop format)
            start_date (Optional[str]): Start date filter
            loops (int): Number of loops (0=until EOF)
            max_log_length (int): Max log line length
            time_tolerance (float): Time tolerance for out-of-order
            output_file (str): Output file path
            csv_file (str): CSV output file path
            logs_dir (str): Log directory
            verbose (bool): Enable verbose logging
            pair_mode (bool): Enable pair mode for start/stop timing
            max_time_delta (float): Max seconds between start/stop or start/start

        Returns:
            Tuple[List[str], List[List]]: (results, csv_results)
        """
        # Parse start date
        start_datetime = self._parse_start_date(start_date, verbose)
        if verbose and start_datetime:
            get_logger().log_info(f"Parsed start_datetime: {start_datetime} (timezone: {start_datetime.tzinfo})")

        # Build variables dict
        variables = {'hostname': hostname}

        # Apply variable substitution
        self._apply_variable_substitution(blocks, variables, verbose)

        # Expand wildcards
        self._expand_wildcards_in_blocks(blocks, logs_dir, start_datetime, verbose)

        # Initialize results
        results = []
        csv_results = []

        if verbose:
            get_logger().log_info(f"Loaded {len(blocks)} blocks")

        # Print header
        header = "Cumulative(s)\tDelta(HH:MM:SS)\tBlock Label          \tLog File  \tLog Line"
        banner = "-------------\t-------------\t----------------------\t------------\t--------"
        get_logger().log_info("\n" + header)
        get_logger().log_info(banner)

        # Main processing loop
        loop_count = 0
        while True:
            loop_count += 1

            # Check loop limit
            if loops > 0 and loop_count > loops:
                break

            # Calculate timing summary
            # Total time: from first non-excluded block to latest end (KPI timeframe)
            # KPI time: same as total time minus any blackout phases within that timeframe
            if pair_mode:
                success, kpi_start_time, end_time, blackout_duration = self._process_blocks_pair_mode(
                    blocks, start_datetime, max_log_length, logs_dir, max_time_delta,
                    results, csv_results, verbose
                )
                total_duration_raw = (end_time - kpi_start_time).total_seconds() if kpi_start_time and end_time else 0.0
                kpi_duration = total_duration_raw - blackout_duration  # Subtract only blackout phases within KPI timeframe
                patterns_found = len([r for r in results[len(results)-len(blocks):] if '⚠️' not in r and not r.startswith('✅')])
            else:
                success, patterns_found, kpi_start_time, end_time, blackout_duration = self._process_blocks_sequential(
                    blocks, start_datetime, time_tolerance, max_log_length, logs_dir,
                    results, csv_results, verbose
                )
                total_duration_raw = (end_time - kpi_start_time).total_seconds() if kpi_start_time and end_time else 0.0
                kpi_duration = total_duration_raw - blackout_duration

            if not success:
                if verbose:
                    get_logger().log_info(f"Pass {loop_count} ended - no patterns found")
                break

            total_duration = self._format_duration(total_duration_raw)
            kpi_duration_formatted = self._format_duration(kpi_duration)

            # Extract model info
            model_info = self._extract_model_info(blocks, logs_dir, verbose)
            model_suffix = f" for {model_info}" if model_info else ""

            if blackout_duration > 0:
                summary_line = f"Pass {loop_count:<3}     {total_duration} (KPI: {kpi_duration_formatted})    found {patterns_found} patterns{model_suffix}"
                get_logger().log_info(f"✅ {summary_line} <-----------------------------")
                get_logger().log_info(f"TOTAL TIME: {total_duration} (excluding blackout: {kpi_duration_formatted})")
                if model_info:
                    get_logger().log_info(f"HARDWARE: {model_info}")
            else:
                summary_line = f"Pass {loop_count:<3}     {total_duration}    found {patterns_found} patterns{model_suffix}"
                get_logger().log_info(f"✅ {summary_line} <-----------------------------")
                get_logger().log_info(f"TOTAL TIME: {total_duration}")
                if model_info:
                    get_logger().log_info(f"HARDWARE: {model_info}")

            # Add summary to results
            results.append("✅ " + summary_line + "\n")
            
            # Add KPI timing metadata for display
            if kpi_start_time:
                results.append(f"KPI_START_TIME={kpi_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                # Find first non-excluded block to get start pattern
                for block in blocks:
                    if not block.get('exclude_from_kpi', False):
                        start_pattern = block.get('start', block.get('patterns', [''])[0] if 'patterns' in block else '')
                        if isinstance(start_pattern, list):
                            start_pattern = start_pattern[0]
                        results.append(f"KPI_START_PATTERN={start_pattern}\n")
                        break
            if end_time:
                results.append(f"KPI_END_TIME={end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
                # Find last non-excluded block to get stop pattern
                for block in reversed(blocks):
                    if not block.get('exclude_from_kpi', False):
                        stop_pattern = block.get('stop', block.get('patterns', [''])[-1] if 'patterns' in block else '')
                        if isinstance(stop_pattern, list):
                            stop_pattern = stop_pattern[0]
                        results.append(f"KPI_END_PATTERN={stop_pattern}\n")
                        break
            
            csv_results.append([f"Pass {loop_count}", total_duration, f"found {patterns_found} patterns", "", ""])

            if loops == 1:
                break

            # Continue from where we left off - advance by 1 second to find next unlock
            start_datetime = end_time + timedelta(seconds=1) if end_time else start_datetime

            get_logger().log_info("\n-------------------------------------------------------------")

        # Write output files
        self._write_output_file(output_file, header, banner, results, verbose)
        self._write_csv_file(csv_file, csv_results, verbose)

        return results, csv_results

    def parse_and_display_results(self, results: List[str]) -> None:
        """
        Parse KPI results and display in formatted table.
        
        Args:
            results (List[str]): Raw results from calculate_kpi
        """
        table_data = []
        summary_line = ""
        total_time = ""
        kpi_time = ""
        kpi_start_time = ""
        kpi_end_time = ""
        kpi_start_pattern = ""
        kpi_end_pattern = ""
        patterns_count = ""
        model_info = ""
        
        for line in results:
            if line.strip():
                if line.startswith('✅'):
                    summary_line = line.strip()
                    parts = summary_line.split()
                    if len(parts) >= 4:
                        for part in parts:
                            if ':' in part and '.' in part and len(part.split(':')) == 3:
                                total_time = part
                                break
                    # Extract KPI time from (KPI: HH:MM:SS.xxx) format
                    if '(KPI:' in summary_line:
                        kpi_match = re.search(r'\(KPI: ([0-9:]+\.[0-9]+)\)', summary_line)
                        if kpi_match:
                            kpi_time = kpi_match.group(1)
                    if 'found' in summary_line and 'patterns' in summary_line:
                        idx = summary_line.index('found')
                        patterns_count = summary_line[idx:].split('patterns')[0].replace('found', '').strip()
                    if 'for' in summary_line:
                        model_info = summary_line.split('for', 1)[1].strip()
                elif line.startswith('KPI_START_TIME='):
                    kpi_start_time = line.split('=')[1].strip()
                elif line.startswith('KPI_END_TIME='):
                    kpi_end_time = line.split('=')[1].strip()
                elif line.startswith('KPI_START_PATTERN='):
                    kpi_start_pattern = line.split('=', 1)[1].strip()
                elif line.startswith('KPI_END_PATTERN='):
                    kpi_end_pattern = line.split('=', 1)[1].strip()
                else:
                    parts = line.split('\t')
                    if len(parts) >= 5:
                        table_data.append([parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip(), parts[4].strip()])
        
        if total_time:
            summary_row = ['TOTAL TIME', total_time, f'✅ Found {patterns_count} patterns', '', model_info if model_info else '']
            table_data.append(summary_row)
            
            # Add KPI time row if blackout duration exists
            if kpi_time:
                kpi_row = ['KPI TIME', kpi_time, '(excluding blackout)', '', '']
                table_data.append(kpi_row)
            
            # Add KPI start/end timestamps with patterns
            if kpi_start_time:
                start_row = ['KPI START', kpi_start_time, 'First non-excluded block start', '', kpi_start_pattern[:80] if kpi_start_pattern else '']
                table_data.append(start_row)
            if kpi_end_time:
                end_row = ['KPI END', kpi_end_time, 'Last non-excluded block stop', '', kpi_end_pattern[:80] if kpi_end_pattern else '']
                table_data.append(end_row)
            
            # Add hardware info row if available
            if model_info:
                hardware_row = ['HARDWARE', '', model_info, '', '']
                table_data.append(hardware_row)
        
        if table_data:
            table_output = tabulate(table_data, 
                                   headers=['Cumulative(s)', 'Delta Time', 'Block Label', 'Log File', 'Log Line'],
                                   tablefmt='grid')
            get_logger().log_info("\n" + table_output)
            
            if total_time:
                get_logger().log_info(f"\n=== TOTAL TIME: {total_time} ===")
        
        get_logger().log_info(f"\nKPI calculation complete. Found {len(table_data)-1} timing points.")
        get_logger().log_info("Results saved to /tmp/profile.timing and /tmp/profile.csv")

    def _parse_start_date(self, start_date: Optional[str], verbose: bool) -> Optional[datetime]:
        """Parse start date string or datetime object.
        
        Args:
            start_date (Optional[str]): Start date as string or datetime object
            verbose (bool): Enable verbose logging
            
        Returns:
            Optional[datetime]: Parsed datetime or None
        """
        if not start_date:
            return None
        
        # If already a datetime object, return it
        if isinstance(start_date, datetime):
            if verbose:
                get_logger().log_info(f"Using datetime object: {start_date}")
            return start_date
        
        # Parse string
        try:
            if 'T' in start_date:
                dt = datetime.fromisoformat(start_date)
            else:
                dt = datetime.fromisoformat(start_date + 'T00:00:00')
            if verbose:
                get_logger().log_info(f"Parsed start-date: {dt}")
            return dt
        except ValueError:
            get_logger().log_info(f"Invalid start date format: {start_date}")
            return None

    def _parse_timestamp(self, line: str, verbose: bool = False) -> Optional[datetime]:
        """Extract timestamp from log line (sysinv or ISO format)."""
        # sysinv format: "sysinv 2024-01-06 12:30:45.123"
        if line.startswith('sysinv '):
            match = re.search(r'sysinv (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
            if match:
                try:
                    dt = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S.%f')
                    if verbose:
                        get_logger().log_info(f"Parsed sysinv timestamp: {dt} from {match.group(1)}")
                    return dt
                except:
                    pass

        # ISO format with milliseconds: "2024-01-06T12:30:45.123"
        match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})', line)
        if match:
            try:
                dt = datetime.fromisoformat(match.group(1))
                if verbose:
                    get_logger().log_info(f"Parsed ISO timestamp: {dt} from {match.group(1)}")
                return dt
            except:
                pass
        
        # ISO format with microseconds: "2024-01-06T12:30:45.123456"
        match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6})', line)
        if match:
            try:
                dt = datetime.fromisoformat(match.group(1))
                if verbose:
                    get_logger().log_info(f"Parsed ISO microsecond timestamp: {dt} from {match.group(1)}")
                return dt
            except:
                pass
        
        if verbose:
            get_logger().log_info(f"Could not parse timestamp from line: {line[:100]}...")
        return None

    def _substitute_variables(self, text: str, variables: Dict[str, str]) -> str:
        """Substitute variables in text.
        
        Args:
            text (str): Text with {variable} placeholders
            variables (Dict[str, str]): Variable substitutions
            
        Returns:
            str: Text with variables substituted
        """
        try:
            return text.format(**variables)
        except KeyError as e:
            get_logger().log_info(f"Warning: Variable {e} not defined")
            return text

    def _apply_variable_substitution(self, blocks: List[Dict], variables: Dict[str, str], verbose: bool) -> None:
        """Apply variable substitution to all patterns."""
        for block in blocks:
            # Handle pair mode blocks (start/stop format)
            if 'start' in block and 'stop' in block:
                # Handle start pattern (string or list)
                if isinstance(block['start'], list):
                    block['start'] = [self._substitute_variables(p, variables) for p in block['start']]
                else:
                    block['start'] = self._substitute_variables(block['start'], variables)
                
                # Handle stop pattern (string or list)
                if isinstance(block['stop'], list):
                    block['stop'] = [self._substitute_variables(p, variables) for p in block['stop']]
                else:
                    block['stop'] = self._substitute_variables(block['stop'], variables)
                
                if verbose:
                    get_logger().log_info(f"Block '{block['label']}' start/stop after substitution: {block['start']} / {block['stop']}")
            # Handle sequential mode blocks (patterns format)
            elif 'patterns' in block:
                for i, pattern in enumerate(block['patterns']):
                    if isinstance(pattern, list):
                        block['patterns'][i] = [self._substitute_variables(p, variables) for p in pattern]
                    else:
                        block['patterns'][i] = self._substitute_variables(pattern, variables)
                if verbose:
                    get_logger().log_info(f"Block '{block['label']}' patterns after substitution: {block['patterns']}")

    def _expand_wildcards_in_blocks(self, blocks: List[Dict], logs_dir: str, start_date: Optional[datetime], verbose: bool) -> None:
        """Expand wildcard patterns in file specifications."""
        for block in blocks:
            file_spec = block['file']

            if isinstance(file_spec, list):
                expanded = []
                for f in file_spec:
                    if '*' in f:
                        expanded.extend(self._expand_and_sort_log_files(logs_dir, f, start_date, verbose))
                    else:
                        expanded.append(f)
                block['file'] = expanded
            elif isinstance(file_spec, str) and '*' in file_spec:
                block['file'] = self._expand_and_sort_log_files(logs_dir, file_spec, start_date, verbose)

            if verbose:
                get_logger().log_info(f"Block '{block['label']}' expanded files: {block['file']}")

    def _expand_and_sort_log_files(self, logs_dir: str, file_pattern: str, start_date: Optional[datetime], verbose: bool) -> List[str]:
        """Expand wildcard and sort files by date proximity."""
        if '*' not in file_pattern:
            return [file_pattern]

        # Find matching files
        cmd = f"find {logs_dir} -name '{file_pattern}' 2>/dev/null"
        result = self.ssh_connection.send(cmd)

        if not result or not result[0].strip():
            if verbose:
                get_logger().log_info(f"Warning: No files matched pattern '{file_pattern}'")
            return [file_pattern]

        matched_files = [f.strip() for f in result if f.strip()]

        # Get file mtimes and basenames
        file_info = []
        for filepath in matched_files:
            cmd = f"stat -c %Y {filepath} 2>/dev/null"
            mtime_result = self.ssh_connection.send(cmd)
            if mtime_result and mtime_result[0].strip().isdigit():
                mtime = int(mtime_result[0].strip())
                basename = filepath.split('/')[-1]
                file_info.append((basename, mtime))

        if not file_info:
            return [file_pattern]

        # Sort by date proximity
        if start_date:
            start_timestamp = start_date.timestamp()
            file_info.sort(key=lambda x: abs(x[1] - start_timestamp))
        else:
            file_info.sort(key=lambda x: x[1], reverse=True)

        sorted_files = [f[0] for f in file_info]

        if verbose:
            get_logger().log_info(f"Expanded '{file_pattern}' to {len(sorted_files)} files: {sorted_files}")

        return sorted_files

    def _format_duration(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS.xxx format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def _format_log_line_for_output(self, log_line: str, filename: str) -> str:
        """Format log line, removing sysinv prefix."""
        if filename.startswith('sysinv.log') and log_line.startswith('sysinv '):
            return log_line[7:]
        return log_line

    def _extract_model_info(self, blocks: List[Dict], logs_dir: str, verbose: bool) -> str:
        """Extract model information from mtcAgent logs or system info.
        
        Args:
            blocks (List[Dict]): Block definitions (not used, kept for compatibility)
            logs_dir (str): Log directory path
            verbose (bool): Enable verbose logging
            
        Returns:
            str: Model info string or empty string
        """
        manufacturer_log_files = ['mtcAgent.log', 'mtcAgent.log.1.gz']

        # Try to extract from mtcAgent logs first
        for filename in manufacturer_log_files:
            filepath = f"{logs_dir}/{filename}"
            
            check_cmd = f"test -f {filepath} && echo 'exists' || echo 'missing'"
            check_result = self.ssh_connection.send(check_cmd)
            if not check_result or 'missing' in check_result[0]:
                continue

            if filename.endswith('.gz'):
                cmd = f"zcat {filepath} 2>/dev/null | grep 'manufacturer is'"
            else:
                cmd = f"grep 'manufacturer is' {filepath} 2>/dev/null"
            
            result = self.ssh_connection.send(cmd)

            if result:
                for line in result:
                    if not line.strip():
                        continue
                    if "manufacturer is" in line:
                        match = re.search(r'model:(.+)', line)
                        if match:
                            model_info = match.group(1).strip()
                            if verbose:
                                get_logger().log_info(f"Found model info: {model_info}")
                            return f"model:{model_info}"

        # Fallback: Try to get hardware info from dmidecode
        if verbose:
            get_logger().log_info("Model info not found in logs, trying dmidecode")
        
        dmi_cmd = "sudo dmidecode -t system 2>/dev/null | grep -E 'Manufacturer|Product Name' | head -2"
        dmi_result = self.ssh_connection.send(dmi_cmd)
        
        if dmi_result and len(dmi_result) >= 2:
            manufacturer = ""
            product = ""
            for line in dmi_result:
                if "Manufacturer:" in line:
                    manufacturer = line.split(":", 1)[1].strip()
                elif "Product Name:" in line:
                    product = line.split(":", 1)[1].strip()
            
            if manufacturer and product:
                model_info = f"{manufacturer} {product}"
                if verbose:
                    get_logger().log_info(f"Found hardware info: {model_info}")
                return model_info

        return ""

    def _find_pattern_in_files_all_matches(self, logs_dir: str, filenames: List[str], pattern: str,
                                           after_timestamp: Optional[datetime], verbose: bool,
                                           block_label: str) -> List[Tuple]:
        """Find ALL matches for a pattern in files (used for sort mode).
        
        Args:
            logs_dir (str): Log directory path
            filenames (List[str]): List of filenames to search
            pattern (str): Pattern to search for
            after_timestamp (Optional[datetime]): Only return matches after this time
            verbose (bool): Enable verbose logging
            block_label (str): Block label for error messages
            
        Returns:
            List[Tuple]: List of (timestamp, log_line, filename) tuples
        """
        matches = []
        if isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            filepath = f"{logs_dir}/{filename}"

            check_cmd = f"test -f {filepath} && echo 'exists' || echo 'missing'"
            check_result = self.ssh_connection.send(check_cmd)
            if not check_result or 'missing' in check_result[0]:
                continue

            is_gzipped = filename.endswith('.gz')
            if is_gzipped:
                cmd = f"zcat {filepath} 2>/dev/null | grep -F '{pattern}'"
            else:
                cmd = f"grep -F '{pattern}' {filepath} 2>/dev/null"

            result = self.ssh_connection.send(cmd)

            if result:
                for line in result:
                    if not line.strip():
                        continue

                    line = line.strip()
                    timestamp = self._parse_timestamp(line, verbose)

                    if timestamp and (not after_timestamp or timestamp > after_timestamp):
                        formatted_line = self._format_log_line_for_output(line, filename)
                        matches.append((timestamp, formatted_line, filename))

        return matches

    def _find_pattern_lpmp_style(self, logs_dir: str, filenames: List[str], pattern: str,
                                start_date: Optional[datetime], verbose: bool, block_label: str,
                                max_time_delta: Optional[float] = None, ignore_max_time_delta: bool = False,
                                allow_before_start: bool = False) -> Optional[Tuple]:
        """Find pattern using LPMP logic with regex support and timestamp filter."""
        if isinstance(filenames, str):
            filenames = [filenames]

        # Detect if pattern is regex (starts with 'r' prefix indicator or contains regex chars)
        use_regex = pattern.startswith('r\'') or any(c in pattern for c in ['.', '*', '+', '?', '^', '$', '[', ']', '{', '}', '(', ')', '|', '\\'])
        
        for filename in filenames:
            filepath = f"{logs_dir}/{filename}"

            # Check if file exists
            check_cmd = f"test -f {filepath} && echo 'exists' || echo 'missing'"
            check_result = self.ssh_connection.send(check_cmd)
            if not check_result or 'missing' in check_result[0]:
                continue

            if verbose:
                get_logger().log_info(f"Searching for '{pattern}' in {filename} (regex={use_regex})")

            # Use grep with or without regex based on pattern type
            is_gzipped = filename.endswith('.gz')
            if use_regex:
                # Remove 'r' prefix if present
                clean_pattern = pattern[2:-1] if pattern.startswith('r\'') else pattern
                if is_gzipped:
                    cmd = f"zcat {filepath} 2>/dev/null | grep -E '{clean_pattern}'"
                else:
                    cmd = f"grep -E '{clean_pattern}' {filepath} 2>/dev/null"
            else:
                # Literal string matching
                if is_gzipped:
                    cmd = f"zcat {filepath} 2>/dev/null | grep -F '{pattern}'"
                else:
                    cmd = f"grep -F '{pattern}' {filepath} 2>/dev/null"

            result = self.ssh_connection.send(cmd)

            if result:
                # Find the FIRST match after start_date (closest to start_date)
                best_match = None
                best_timestamp = None
                
                for line in result:
                    if not line.strip():
                        continue
                    
                    line = line.strip()
                    timestamp = self._parse_timestamp(line, verbose)

                    if timestamp:
                        if start_date:
                            if timestamp <= start_date:
                                if verbose:
                                    get_logger().log_info(f"REJECTING: {pattern} at {timestamp} (before or equal to start_date {start_date})")
                                continue
                            
                            # Additional constraint: prevent jumping to different unlock sequences
                            # Reasonable unlock sequence should complete within 2 hours (7200s)
                            time_from_start = (timestamp - start_date).total_seconds()
                            if time_from_start > 7200:  # 2 hours max
                                if verbose:
                                    get_logger().log_info(f"Skipping match at {timestamp} (too far from start_date: {time_from_start}s > 7200s)")
                                continue
                            
                            # Keep the earliest match after start_date
                            if best_timestamp is None or timestamp < best_timestamp:
                                best_match = line
                                best_timestamp = timestamp
                                if verbose:
                                    get_logger().log_info(f"NEW BEST: {pattern} at {timestamp} (closest to start_date {start_date})")
                        else:
                            # No start_date filter - take first match
                            if verbose:
                                get_logger().log_info(f"NO start_date filter - ACCEPTING: {pattern} at {timestamp}")
                            formatted_line = self._format_log_line_for_output(line, filename)
                            return (timestamp, formatted_line, filename)

                # Return the best match found
                if best_match and best_timestamp:
                    if verbose:
                        get_logger().log_info(f"Found pattern at {best_timestamp} in {filename}")
                    formatted_line = self._format_log_line_for_output(best_match, filename)
                    return (best_timestamp, formatted_line, filename)

        return None

    def _find_pattern_in_files_with_fallback(self, logs_dir: str, filenames: List[str], pattern: str,
                                            file_positions: Dict[str, int], after_timestamp: Optional[datetime],
                                            verbose: bool, suppress_error: bool, block_label: str) -> Optional[Tuple]:
        """Find pattern in files with improved fallback logic."""
        if isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            filepath = f"{logs_dir}/{filename}"

            # Check if file exists
            check_cmd = f"test -f {filepath} && echo 'exists' || echo 'missing'"
            check_result = self.ssh_connection.send(check_cmd)
            if not check_result or 'missing' in check_result[0]:
                if verbose:
                    get_logger().log_info(f"File {filepath} not found, trying next...")
                continue

            current_pos = file_positions.get(filename, 0)
            if verbose:
                get_logger().log_info(f"Searching for '{pattern}' in {filename} from position {current_pos}")

            # Handle compressed files
            is_gzipped = filename.endswith('.gz')
            
            # First try: search from current position with timestamp filter
            if after_timestamp:
                if is_gzipped:
                    cmd = f"zcat {filepath} 2>/dev/null | tail -n +{current_pos + 1} | grep -F '{pattern}'"
                else:
                    cmd = f"tail -n +{current_pos + 1} {filepath} 2>/dev/null | grep -F '{pattern}'"
            else:
                if is_gzipped:
                    cmd = f"zcat {filepath} 2>/dev/null | tail -n +{current_pos + 1} | grep -F '{pattern}' | head -1"
                else:
                    cmd = f"tail -n +{current_pos + 1} {filepath} 2>/dev/null | grep -F '{pattern}' | head -1"

            result = self.ssh_connection.send(cmd)
            
            # Process results with timestamp filtering
            if result:
                for line in result:
                    if not line.strip():
                        continue
                    
                    line = line.strip()
                    timestamp = self._parse_timestamp(line, verbose)

                    if timestamp:
                        if after_timestamp and timestamp <= after_timestamp:
                            if verbose:
                                get_logger().log_info(f"Skipping match at {timestamp} (before {after_timestamp})")
                            continue

                        if verbose:
                            get_logger().log_info(f"Found pattern at {timestamp} in {filename}")

                        formatted_line = self._format_log_line_for_output(line, filename)
                        new_pos = 0 if is_gzipped else current_pos + 1
                        return (timestamp, new_pos, formatted_line, filename)
            
            # Second try: if no match found and we have a timestamp constraint, 
            # try searching from beginning of file (pattern might be earlier)
            if after_timestamp and current_pos > 0:
                if verbose:
                    get_logger().log_info(f"No match from position {current_pos}, trying from beginning of {filename}")
                
                if is_gzipped:
                    cmd = f"zcat {filepath} 2>/dev/null | grep -F '{pattern}'"
                else:
                    cmd = f"grep -F '{pattern}' {filepath} 2>/dev/null"
                
                result = self.ssh_connection.send(cmd)
                
                if result:
                    for line in result:
                        if not line.strip():
                            continue
                        
                        line = line.strip()
                        timestamp = self._parse_timestamp(line, verbose)

                        if timestamp:
                            if after_timestamp and timestamp <= after_timestamp:
                                continue

                            if verbose:
                                get_logger().log_info(f"Found pattern at {timestamp} in {filename} (full file search)")

                            formatted_line = self._format_log_line_for_output(line, filename)
                            new_pos = 0 if is_gzipped else 1
                            return (timestamp, new_pos, formatted_line, filename)

        # Pattern not found
        if not suppress_error:
            file_list = ', '.join(filenames)
            label_info = f" for block '{block_label}'" if block_label else ""
            get_logger().log_info(f"⚠️ Error: Pattern '{pattern}' not found in any of: {file_list}{label_info}")

        return None

    def _find_pattern_in_files(self, logs_dir: str, filenames: List[str], pattern: str,
                              start_pos: int, after_timestamp: Optional[datetime],
                              verbose: bool, suppress_error: bool, block_label: str) -> Optional[Tuple]:
        """Find pattern in files with position tracking."""
        if isinstance(filenames, str):
            filenames = [filenames]

        for filename in filenames:
            filepath = f"{logs_dir}/{filename}"

            # Check if file exists
            check_cmd = f"test -f {filepath} && echo 'exists' || echo 'missing'"
            check_result = self.ssh_connection.send(check_cmd)
            if not check_result or 'missing' in check_result[0]:
                if verbose:
                    get_logger().log_info(f"File {filepath} not found, trying next...")
                continue

            if verbose:
                get_logger().log_info(f"Searching for '{pattern}' in {filename} from position {start_pos}")

            # Handle compressed files
            is_gzipped = filename.endswith('.gz')
            if is_gzipped:
                if after_timestamp:
                    cmd = f"zcat {filepath} 2>/dev/null | tail -n +{start_pos + 1} | grep -F '{pattern}'"
                else:
                    cmd = f"zcat {filepath} 2>/dev/null | tail -n +{start_pos + 1} | grep -F '{pattern}' | head -1"
            else:
                if after_timestamp:
                    cmd = f"tail -n +{start_pos + 1} {filepath} 2>/dev/null | grep -F '{pattern}'"
                else:
                    cmd = f"tail -n +{start_pos + 1} {filepath} 2>/dev/null | grep -F '{pattern}' | head -1"

            result = self.ssh_connection.send(cmd)

            if result:
                for line in result:
                    if not line.strip():
                        continue
                    
                    line = line.strip()
                    timestamp = self._parse_timestamp(line, verbose)

                    if timestamp:
                        if after_timestamp and timestamp <= after_timestamp:
                            if verbose:
                                get_logger().log_info(f"Skipping match at {timestamp} (before {after_timestamp})")
                            continue

                        if verbose:
                            get_logger().log_info(f"Found pattern at {timestamp} in {filename}")

                        formatted_line = self._format_log_line_for_output(line, filename)
                        new_pos = 0 if is_gzipped else start_pos + 1
                        return (timestamp, new_pos, formatted_line, filename)

        # Pattern not found
        if not suppress_error:
            file_list = ', '.join(filenames)
            label_info = f" for block '{block_label}'" if block_label else ""
            get_logger().log_info(f"⚠️ Error: Pattern '{pattern}' not found in any of: {file_list}{label_info}")

        return None

    def _process_blocks_with_queue(self, blocks: List[Dict], start_date: Optional[datetime],
                                  time_tolerance: float, max_log_length: int, logs_dir: str,
                                  results: List[str], csv_results: List[List], verbose: bool) -> Tuple:
        """Process blocks with queuing for missing patterns (LPMP queue logic)."""
        pending_queue = []
        file_positions = {}
        start_time = None
        prev_timestamp = start_date
        patterns_found = 0
        blackout_duration = 0.0

        def try_block(block, current_pos, after_timestamp):
            """Try to find all patterns for a block sequentially."""
            last_result = None
            temp_pos = current_pos
            temp_timestamp = after_timestamp

            for pattern in block['patterns']:
                pattern_found = False
                if isinstance(pattern, list):
                    for alt_pattern in pattern:
                        result = self._find_pattern_in_files(
                            logs_dir, block['file'], alt_pattern, temp_pos, temp_timestamp,
                            verbose, suppress_error=True, block_label=block['label']
                        )
                        if result is not None:
                            timestamp, new_pos, log_line, actual_filename = result
                            pattern_found = True
                            last_result = result
                            temp_pos = new_pos
                            temp_timestamp = timestamp
                            break
                else:
                    result = self._find_pattern_in_files(
                        logs_dir, block['file'], pattern, temp_pos, temp_timestamp,
                        verbose, suppress_error=True, block_label=block['label']
                    )
                    if result is not None:
                        timestamp, new_pos, log_line, actual_filename = result
                        pattern_found = True
                        last_result = result
                        temp_pos = new_pos
                        temp_timestamp = timestamp

                if not pattern_found:
                    return False, None

            return True, last_result

        def output_result(block, timestamp, log_line, actual_filename, start_time, prev_timestamp):
            """Generate output for a successful match."""
            nonlocal patterns_found
            patterns_found += 1

            if start_time is None:
                start_time = timestamp
                cumulative = 0.0
                delta = 0.0
            else:
                delta = (timestamp - prev_timestamp).total_seconds()
                cumulative = (timestamp - start_time).total_seconds()

            delta_formatted = self._format_duration(delta)
            filename_padded = f"{actual_filename:<10}"
            label_padded = f"{block['label']:<20}"
            truncated_log = log_line[:max_log_length]

            result_line = f"{cumulative:8.3f}\t{delta_formatted:>12}\t{label_padded}\t{filename_padded}\t{truncated_log}"
            results.append(result_line)
            csv_results.append([cumulative, delta_formatted, block['label'], actual_filename, truncated_log])
            get_logger().log_info(result_line)

            return start_time, timestamp

        def output_optional_skip(block, start_time, prev_timestamp):
            """Generate output for skipped optional block."""
            cumulative = (prev_timestamp - start_time).total_seconds() if start_time and prev_timestamp else 0.0
            delta_formatted = "??:??:??.???"
            filename_padded = f"{'N/A':<10}"
            label_padded = f"{block['label']:<20}"
            truncated_log = "⚠️ Pattern not found (optional block skipped)"

            result_line = f"{cumulative:8.3f}\t{delta_formatted:>12}\t{label_padded}\t{filename_padded}\t{truncated_log}"
            results.append(result_line)
            csv_results.append([cumulative, delta_formatted, block['label'], 'N/A', truncated_log])
            get_logger().log_info(result_line)

        # Process each block
        for block_index, block in enumerate(blocks):
            if not block['file'] or (not block.get('patterns') and not (block.get('start') and block.get('stop'))):
                continue

            # Try queued blocks first
            resolved_queue = []
            for queued_block in pending_queue:
                file_key = str(queued_block['file']) if isinstance(queued_block['file'], list) else queued_block['file']
                current_pos = file_positions.get(file_key, 0)
                after_timestamp = prev_timestamp - timedelta(seconds=time_tolerance) if prev_timestamp else None

                success, result = try_block(queued_block, current_pos, after_timestamp)
                if success:
                    timestamp, new_pos, log_line, actual_filename = result
                    start_time, prev_timestamp = output_result(
                        queued_block, timestamp, log_line, actual_filename,
                        start_time, prev_timestamp)

                    matched_file_key = actual_filename if isinstance(queued_block['file'], list) else file_key
                    file_positions[matched_file_key] = new_pos
                    resolved_queue.append(queued_block)

            for resolved in resolved_queue:
                pending_queue.remove(resolved)

            # Try current block
            file_key = str(block['file']) if isinstance(block['file'], list) else block['file']
            current_pos = file_positions.get(file_key, 0)
            after_timestamp = prev_timestamp - timedelta(seconds=time_tolerance) if prev_timestamp else None

            success, result = try_block(block, current_pos, after_timestamp)
            if success:
                timestamp, new_pos, log_line, actual_filename = result
                start_time, prev_timestamp = output_result(
                    block, timestamp, log_line, actual_filename,
                    start_time, prev_timestamp)

                matched_file_key = actual_filename if isinstance(block['file'], list) else file_key
                file_positions[matched_file_key] = new_pos
            else:
                if block.get('optional', False):
                    output_optional_skip(block, start_time, prev_timestamp)
                else:
                    pending_queue.append(block)

        # Handle remaining queued blocks
        for queued_block in pending_queue:
            if queued_block.get('optional', False):
                output_optional_skip(queued_block, start_time, prev_timestamp)
            else:
                files_str = ', '.join(queued_block['file']) if isinstance(queued_block['file'], list) else queued_block['file']
                patterns_str = ', '.join([str(p) for p in queued_block['patterns']])
                get_logger().log_info(f"⚠️ Error: Required pattern(s) '{patterns_str}' not found in file(s) '{files_str}' for block '{queued_block['label']}'")

        return patterns_found > 0, patterns_found, start_time, prev_timestamp, blackout_duration

    def _process_blocks_sequential(self, blocks: List[Dict], start_date: Optional[datetime],
                                  time_tolerance: float, max_log_length: int, logs_dir: str,
                                  results: List[str], csv_results: List[List], verbose: bool) -> Tuple:
        """Process blocks sequentially with chronological post-sorting (LPMP logic)."""
        file_positions = {}
        start_time = None
        prev_timestamp = start_date
        patterns_found = 0
        temp_results = []
        blackout_duration = 0.0

        for block_index, block in enumerate(blocks):
            if not block['file'] or not block.get('patterns'):
                continue

            file_key = str(block['file']) if isinstance(block['file'], list) else block['file']
            current_pos = file_positions.get(file_key, 0)
            after_timestamp = prev_timestamp - timedelta(seconds=time_tolerance) if prev_timestamp else None

            block_completed = True
            last_result = None

            # Handle both patterns and start/stop format
            if 'start' in block and 'stop' in block:
                patterns_to_process = [block['start'], block['stop']]
            else:
                patterns_to_process = block['patterns']

            for pattern in patterns_to_process:
                pattern_found = False
                if isinstance(pattern, list):
                    for alt_pattern in pattern:
                        result = self._find_pattern_in_files(
                            logs_dir, block['file'], alt_pattern, current_pos, after_timestamp,
                            verbose, suppress_error=True, block_label=block['label']
                        )
                        if result is not None:
                            timestamp, new_pos, log_line, actual_filename = result
                            pattern_found = True
                            last_result = result
                            matched_file_key = actual_filename if isinstance(block['file'], list) else file_key
                            file_positions[matched_file_key] = new_pos
                            current_pos = new_pos
                            after_timestamp = timestamp
                            break
                else:
                    result = self._find_pattern_in_files(
                        logs_dir, block['file'], pattern, current_pos, after_timestamp,
                        verbose, suppress_error=True, block_label=block['label']
                    )
                    if result is not None:
                        timestamp, new_pos, log_line, actual_filename = result
                        pattern_found = True
                        last_result = result
                        matched_file_key = actual_filename if isinstance(block['file'], list) else file_key
                        file_positions[matched_file_key] = new_pos
                        current_pos = new_pos
                        after_timestamp = timestamp

                if not pattern_found:
                    block_completed = False
                    break

            if block_completed and last_result:
                timestamp, new_pos, log_line, actual_filename = last_result
                patterns_found += 1

                temp_results.append({
                    'timestamp': timestamp,
                    'block': block,
                    'log_line': log_line,
                    'actual_filename': actual_filename
                })

                prev_timestamp = timestamp
            else:
                files_str = ', '.join(block['file']) if isinstance(block['file'], list) else block['file']
                if block.get('optional', False):
                    if 'start' in block and 'stop' in block:
                        patterns_str = f"start: '{block['start']}', stop: '{block['stop']}'"
                    else:
                        patterns_str = ', '.join([str(p) for p in block['patterns']])
                    temp_results.append({
                        'timestamp': None,
                        'block': block,
                        'log_line': f"⚠️ Pattern '{patterns_str}' not found in file(s) '{files_str}': (optional block skipped)",
                        'actual_filename': 'N/A'
                    })
                else:
                    if 'start' in block and 'stop' in block:
                        patterns_str = f"start: '{block['start']}', stop: '{block['stop']}'"
                    else:
                        patterns_str = ', '.join([str(p) for p in block['patterns']])
                    get_logger().log_info(f"⚠️ Error: Required pattern(s) '{patterns_str}' not found in file(s) '{files_str}' for block '{block['label']}'")

                    if temp_results:
                        temp_results.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.max)
                        self._output_sorted_results(temp_results, start_time, max_log_length, results, csv_results)

                    return False, patterns_found, start_time, prev_timestamp, blackout_duration

        # Sort and output results
        temp_results.sort(key=lambda x: x['timestamp'] if x['timestamp'] else datetime.max)
        start_time, end_time = self._output_sorted_results(temp_results, start_time, max_log_length, results, csv_results)

        return patterns_found > 0, patterns_found, start_time, end_time, blackout_duration

    def _output_sorted_results(self, temp_results: List[Dict], start_time: Optional[datetime],
                              max_log_length: int, results: List[str], csv_results: List[List]) -> Tuple:
        """Output sorted results with proper timing calculations."""
        prev_timestamp = None
        end_time = None

        for result_data in temp_results:
            timestamp = result_data['timestamp']
            block = result_data['block']
            log_line = result_data['log_line']
            actual_filename = result_data['actual_filename']

            if timestamp is None:
                cumulative = (prev_timestamp - start_time).total_seconds() if start_time and prev_timestamp else 0.0
                delta_formatted = "??:??:??.???"
            else:
                if start_time is None:
                    start_time = timestamp
                    cumulative = 0.0
                    delta = 0.0
                else:
                    delta = (timestamp - prev_timestamp).total_seconds() if prev_timestamp else 0.0
                    cumulative = (timestamp - start_time).total_seconds()

                delta_formatted = self._format_duration(delta)
                prev_timestamp = timestamp
                end_time = timestamp

            filename_padded = f"{actual_filename:<10}"
            label_padded = f"{block['label']:<20}"
            truncated_log = log_line[:max_log_length]

            result_line = f"{cumulative:8.3f}\t{delta_formatted:>12}\t{label_padded}\t{filename_padded}\t{truncated_log}"
            results.append(result_line)
            csv_results.append([cumulative, delta_formatted, block['label'], actual_filename, truncated_log])
            get_logger().log_info(result_line)

        return start_time, end_time

    def _process_blocks_pair_mode(self, blocks: List[Dict], start_date: Optional[datetime],
                                 max_log_length: int, logs_dir: str, max_time_delta: float,
                                 results: List[str], csv_results: List[List], verbose: bool) -> Tuple:
        """
        Process blocks in pair mode for start/stop pattern timing.
        
        Args:
            blocks (List[Dict]): Block definitions with start/stop patterns
            start_date (Optional[datetime]): Start date filter - used as KPI reference time
            max_log_length (int): Max log line length
            logs_dir (str): Log directory path
            max_time_delta (float): Max seconds between start/stop
            results (List[str]): Results accumulator
            csv_results (List[List]): CSV results accumulator
            verbose (bool): Enable verbose logging
            
        Returns:
            Tuple: (success, kpi_start_time, end_time, blackout_duration)
        """
        patterns_found = 0
        kpi_start_time = None
        latest_end_time = None
        blackout_duration = 0.0
        
        # If start_date provided, ensure we only find patterns after that time
        if start_date and verbose:
            get_logger().log_info(f"Using start_date as search filter: {start_date}")
            get_logger().log_info(f"Each block searches independently from start_date")
        
        for block in blocks:
            if not block['file']:
                continue

            # Get start/stop patterns
            if 'start' in block and 'stop' in block:
                start_pattern = block['start']
                stop_pattern = block['stop']
            elif 'patterns' in block and len(block['patterns']) >= 2:
                start_pattern = block['patterns'][0]
                stop_pattern = block['patterns'][1]
            else:
                continue

            # Find start pattern - handle OR patterns (lists)
            # Each phase searches independently from start_date
            start_result = None
            if isinstance(start_pattern, list):
                # OR pattern - try each alternative
                for alt_pattern in start_pattern:
                    start_result = self._find_pattern_lpmp_style(
                        logs_dir, block['file'], alt_pattern, start_date, verbose, block['label']
                    )
                    if start_result:
                        break
            else:
                # Single pattern
                start_result = self._find_pattern_lpmp_style(
                    logs_dir, block['file'], start_pattern, start_date, verbose, block['label']
                )
            
            if not start_result:
                if not block.get('optional', False):
                    self._output_pair_error(block, "Start NOT FOUND !", 0.0, results, csv_results)
                continue

            start_timestamp, start_log_line, start_filename = start_result

            # Find stop pattern - handle OR patterns (lists)
            # For overlapping phases, allow stop pattern to be found before start pattern
            # if it's within the same unlock sequence timeframe
            stop_result = None
            if isinstance(stop_pattern, list):
                # OR pattern - try each alternative
                for alt_pattern in stop_pattern:
                    # First try: search after start_timestamp
                    stop_result = self._find_pattern_lpmp_style(
                        logs_dir, block['file'], alt_pattern, start_timestamp, verbose, block['label'],
                        max_time_delta=block.get('max_time_delta', max_time_delta)
                    )
                    # If not found after start, try searching from original start_date for overlapping phases
                    if not stop_result and start_date:
                        stop_result = self._find_pattern_lpmp_style(
                            logs_dir, block['file'], alt_pattern, start_date, verbose, block['label'],
                            max_time_delta=block.get('max_time_delta', max_time_delta)
                        )
                    # If still not found, search without time constraints within unlock sequence
                    if not stop_result and start_date:
                        stop_result = self._find_pattern_lpmp_style(
                            logs_dir, block['file'], alt_pattern, start_date, verbose, block['label'],
                            max_time_delta=7200  # 2 hour max for unlock sequence
                        )
                    if stop_result:
                        break
            else:
                # Single pattern
                # First try: search after start_timestamp
                stop_result = self._find_pattern_lpmp_style(
                    logs_dir, block['file'], stop_pattern, start_timestamp, verbose, block['label'],
                    max_time_delta=block.get('max_time_delta', max_time_delta)
                )
                # If not found after start, try searching from original start_date for overlapping phases
                if not stop_result and start_date:
                    stop_result = self._find_pattern_lpmp_style(
                        logs_dir, block['file'], stop_pattern, start_date, verbose, block['label'],
                        max_time_delta=block.get('max_time_delta', max_time_delta)
                    )
                # If still not found, search without time constraints within unlock sequence
                if not stop_result and start_date:
                    stop_result = self._find_pattern_lpmp_style(
                        logs_dir, block['file'], stop_pattern, start_date, verbose, block['label'],
                        max_time_delta=7200  # 2 hour max for unlock sequence
                    )
                
            if not stop_result:
                if not block.get('optional', False):
                    error_msg = f"Stop NOT FOUND after {start_timestamp.strftime('%H:%M:%S')}"
                    self._output_pair_error(block, error_msg, 0.0, results, csv_results, start_filename)
                continue

            stop_timestamp, stop_log_line, stop_filename = stop_result
            patterns_found += 1

            # If no start_date provided, use first non-excluded block's start as KPI reference
            if kpi_start_time is None and not block.get('exclude_from_kpi', False):
                kpi_start_time = start_timestamp

            # Track latest end time (only for non-excluded blocks)
            if not block.get('exclude_from_kpi', False):
                if latest_end_time is None or stop_timestamp > latest_end_time:
                    latest_end_time = stop_timestamp

            # Calculate times - always relative to kpi_start_time
            pair_duration = (stop_timestamp - start_timestamp).total_seconds()
            cumulative = (stop_timestamp - kpi_start_time).total_seconds() if kpi_start_time else 0.0

            # Track blackout duration for excluded blocks within KPI timeframe
            if block.get('exclude_from_kpi', False) and kpi_start_time:
                # Only count if block starts after KPI start time
                if start_timestamp >= kpi_start_time:
                    blackout_duration += abs(pair_duration)

            # Format output
            start_time_str = start_timestamp.strftime("%H:%M:%S.%f")[:-3]
            stop_time_str = stop_timestamp.strftime("%H:%M:%S.%f")[:-3]
            
            # Get pattern text for display
            start_pattern_text = block.get('start', '')
            stop_pattern_text = block.get('stop', '')
            if isinstance(start_pattern_text, list):
                start_pattern_text = start_pattern_text[0]
            if isinstance(stop_pattern_text, list):
                stop_pattern_text = stop_pattern_text[0]
            
            # Truncate patterns for display
            start_pattern_short = (start_pattern_text[:40] + '...') if len(start_pattern_text) > 40 else start_pattern_text
            stop_pattern_short = (stop_pattern_text[:40] + '...') if len(stop_pattern_text) > 40 else stop_pattern_text
            
            log_data = f"Start {start_time_str} --> Stop {stop_time_str}: {abs(pair_duration):.3f}s | Patterns: [{start_pattern_short}] -> [{stop_pattern_short}]"
            
            if block.get('exclude_from_kpi', False):
                log_data += " (excluded from KPI)"

            delta_formatted = self._format_duration(abs(pair_duration))
            self._output_result(block, cumulative, delta_formatted, stop_filename, log_data, results, csv_results)

        return patterns_found > 0, kpi_start_time, latest_end_time, blackout_duration

    def _output_result(self, block: Dict, cumulative: float, delta_formatted: str, 
                      filename: str, log_data: str, results: List[str], csv_results: List[List]) -> None:
        """Output a successful result.
        
        Args:
            block (Dict): Block definition
            cumulative (float): Cumulative time in seconds
            delta_formatted (str): Formatted delta time
            filename (str): Log filename
            log_data (str): Log line or timing data
            results (List[str]): Results accumulator
            csv_results (List[List]): CSV results accumulator
        """
        filename_padded = f"{filename:<10}"
        label_padded = f"{block['label']:<20}"
        result_line = f"{cumulative:8.3f}\t{delta_formatted:>12}\t{label_padded}\t{filename_padded}\t{log_data}"
        results.append(result_line)
        csv_results.append([cumulative, delta_formatted, block['label'], filename, log_data])
        get_logger().log_info(result_line)

    def _output_pair_error(self, block: Dict, error_msg: str, cumulative: float, 
                          results: List[str], csv_results: List[List], filename: str = "N/A") -> None:
        """Output a pair mode error.
        
        Args:
            block (Dict): Block definition
            error_msg (str): Error message
            cumulative (float): Cumulative time in seconds
            results (List[str]): Results accumulator
            csv_results (List[List]): CSV results accumulator
            filename (str): Log filename
        """
        delta_formatted = "??:??:??.???"
        filename_padded = f"{filename:<10}"
        label_padded = f"{block['label']:<20}"
        result_line = f"{cumulative:8.3f}\t{delta_formatted:>12}\t{label_padded}\t{filename_padded}\t{error_msg}"
        results.append(result_line)
        csv_results.append([cumulative, delta_formatted, block['label'], filename, error_msg])
        get_logger().log_info(result_line)

    def _write_output_file(self, output_file: str, header: str, banner: str, results: List[str], verbose: bool) -> None:
        """Write output to file."""
        try:
            content = header + "\n" + banner + "\n" + "\n".join(results)
            cmd = f"cat > {output_file} << 'EOF'\n{content}\nEOF"
            self.ssh_connection.send(cmd)
            if verbose:
                get_logger().log_info(f"Results written to {output_file}")
        except Exception as e:
            get_logger().log_info(f"Error writing to {output_file}: {e}")

    def _write_csv_file(self, csv_file: str, csv_results: List[List], verbose: bool) -> None:
        """Write CSV file."""
        if not csv_results:
            return

        try:
            csv_lines = ['Cumulative(s),Delta(HH:MM:SS),Block Label,Log File,Log Line']
            for row in csv_results:
                csv_line = ','.join([str(row[0]), row[1], f'"{row[2]}"', row[3], f'"{row[4]}"'])
                csv_lines.append(csv_line)

            content = '\n'.join(csv_lines)
            cmd = f"cat > {csv_file} << 'EOF'\n{content}\nEOF"
            self.ssh_connection.send(cmd)

            if verbose:
                get_logger().log_info(f"CSV results written to {csv_file}")
        except Exception as e:
            get_logger().log_info(f"Error writing to {csv_file}: {e}")

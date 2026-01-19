from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import re
import os
import yaml
import gzip
import glob

from framework.logging.automation_logger import get_logger
from framework.ssh.ssh_connection import SSHConnection
from keywords.base_keyword import BaseKeyword


class LogPatternMatchingKeywords(BaseKeyword):
    """
    Provides keyword functions for log pattern matching and timing analysis.
    
    Implements LPMP (Log Pattern Matching Profiler) functionality for analyzing
    log files by searching for specific patterns and measuring time intervals.
    
    KEY FEATURES:
    • Multi-file Support: Search across multiple log files with fallback ordering
    • Chronological Ordering: Maintains temporal sequence across file searches
    • Flexible Pattern Matching: Supports single patterns and OR pattern groups
    • Queuing Mechanism: Missing patterns are queued and retried with subsequent blocks
    • Time Filtering: Start analysis from specific timestamps
    • Optional Blocks: Gracefully handle missing patterns with optional flag
    • Variable Substitution: Support for {hostname} and custom variables
    """

    def __init__(self, ssh_connection: SSHConnection):
        """
        Initialize LogPatternMatchingKeywords with an SSH connection.

        Args:
            ssh_connection: SSH connection to the target system

        """
        self.ssh_connection = ssh_connection
        self.file_positions = {}  # Track file positions for chronological ordering

    def analyze_unlock_timing_patterns(self, hostname: str = "controller-0", 
                                     start_time: Optional[datetime] = None,
                                     max_log_length: int = 190,
                                     loops: int = 1,
                                     time_tolerance: float = 1.0,
                                     variables: Optional[Dict[str, str]] = None) -> Dict:
        """
        Analyze unlock timing patterns using predefined YAML configuration.

        Args:
            hostname: Hostname for pattern substitution
            start_time: Start time for analysis
            max_log_length: Maximum log line length in output
            loops: Number of analysis passes (0=until EOF)
            time_tolerance: Time tolerance in seconds for out-of-order entries
            variables: Additional variable substitution dictionary

        Returns:
            Analysis results with timing data

        """
        # Build variable substitution dictionary
        var_dict = {"hostname": hostname}
        if variables:
            var_dict.update(variables)

        # Define unlock pattern configuration with variable substitution
        unlock_config = {
            "blocks": [
                {
                    "label": "Unlock Action Staged",
                    "file": "sysinv.log*",
                    "patterns": ["{hostname} Action staged: unlock"]
                },
                {
                    "label": "mtcAgent Unlock Action",
                    "file": "mtcAgent.log*", 
                    "patterns": ["{hostname} Unlock Action"]
                },
                {
                    "label": "Lazy Reboot Now",
                    "file": "mtcClient.log*",
                    "optional": True,
                    "patterns": ["failsafe reboot script launched"]
                },
                {
                    "label": "Blackout - Boot",
                    "file": "kern.log*",
                    "patterns": ["Kernel command line:"]
                },
                {
                    "label": "mtcClient Start-Up",
                    "file": "mtcClient.log*",
                    "patterns": ["Daemon Start-Up"]
                },
                {
                    "label": "mtcAgent Start-Up",
                    "file": "mtcAgent.log*",
                    "patterns": ["Daemon Start-Up"]
                },
                {
                    "label": "Host Manufacturer",
                    "file": "mtcAgent.log*",
                    "optional": True,
                    "patterns": ["{hostname} manufacturer is "]
                },
                {
                    "label": "Host Enable State",
                    "file": "mtcAgent.log*",
                    "patterns": [["{hostname} is ENABLED", "{hostname} is DEGRADED"]]
                },
                {
                    "label": "K8s Pod Recovery Done",
                    "file": "daemon.log*",
                    "optional": True,
                    "patterns": ["k8s-pod-recovery.service: Succeeded"]
                }
            ]
        }

        # Apply variable substitution to patterns
        self._apply_variable_substitution(unlock_config["blocks"], var_dict)

        # Process the patterns and return results
        return self._process_pattern_blocks_with_loops(
            unlock_config["blocks"], start_time, max_log_length, loops, time_tolerance)

    def _apply_variable_substitution(self, blocks: List[Dict], variables: Dict[str, str]) -> None:
        """
        Apply variable substitution to all patterns in blocks.

        Args:
            blocks: List of pattern block definitions
            variables: Dictionary of variable substitutions

        """
        for block in blocks:
            for i, pattern in enumerate(block["patterns"]):
                if isinstance(pattern, list):
                    # OR patterns - substitute each alternative
                    block["patterns"][i] = [p.format(**variables) for p in pattern]
                else:
                    # Single pattern
                    block["patterns"][i] = pattern.format(**variables)

    def _process_pattern_blocks_with_loops(self, blocks: List[Dict], start_time: Optional[datetime], 
                                         max_log_length: int, loops: int, time_tolerance: float = 1.0) -> Dict:
        """
        Process pattern blocks with loop support and queuing mechanism.

        Args:
            blocks: List of pattern block definitions
            start_time: Start time for filtering
            max_log_length: Maximum log line length
            loops: Number of analysis passes (0=until EOF)
            time_tolerance: Time tolerance in seconds for out-of-order entries

        Returns:
            Processing results with timing data

        """
        all_results = []
        log_dir = "/var/log"
        loop_count = 0
        current_start_time = start_time
        
        while True:
            loop_count += 1
            
            # Check loop limit
            if loops > 0 and loop_count > loops:
                break
            
            get_logger().log_info(f"Starting analysis pass {loop_count}")
            
            # Process blocks with queuing mechanism
            loop_results = self._process_blocks_with_queue(
                blocks, log_dir, current_start_time, max_log_length, time_tolerance)
            
            if not loop_results:
                get_logger().log_info(f"Pass {loop_count} found no patterns")
                break
            
            all_results.extend(loop_results)
            get_logger().log_info(f"Pass {loop_count} found {len(loop_results)} patterns")
            
            # For subsequent passes, continue from where we left off
            if loop_results:
                last_timestamp_str = loop_results[-1]["timestamp"]
                current_start_time = datetime.fromisoformat(last_timestamp_str)
            
            if loops == 1:  # Single pass mode
                break

        return {
            "results": all_results,
            "total_patterns": len(all_results),
            "start_time": all_results[0]["timestamp"] if all_results else None,
            "end_time": all_results[-1]["timestamp"] if all_results else None
        }

    def _process_blocks_with_queue(self, blocks: List[Dict], log_dir: str, 
                                  start_time: Optional[datetime], max_log_length: int,
                                  time_tolerance: float) -> List[Dict]:
        """
        Process blocks with queuing for missing patterns.

        Args:
            blocks: List of pattern block definitions
            log_dir: Directory containing log files
            start_time: Start time for filtering
            max_log_length: Maximum log line length
            time_tolerance: Time tolerance in seconds

        Returns:
            List of result dictionaries

        """
        pending_queue = []  # Queue of blocks waiting to be resolved
        results = []
        first_timestamp = None
        prev_timestamp = start_time
        
        def try_block(block: Dict, after_timestamp: Optional[datetime]) -> Optional[tuple]:
            """Try to find all patterns for a block sequentially."""
            last_result = None
            temp_timestamp = after_timestamp
            
            for pattern in block["patterns"]:
                pattern_found = False
                if isinstance(pattern, list):
                    # OR pattern - try each alternative
                    for alt_pattern in pattern:
                        result = self._find_pattern_in_files(
                            log_dir, block["file"], alt_pattern, temp_timestamp)
                        if result:
                            pattern_found = True
                            last_result = result
                            temp_timestamp = result[0]
                            break
                    if not pattern_found:
                        files_str = ', '.join(block["file"]) if isinstance(block["file"], list) else block["file"]
                        get_logger().log_info(f"Pattern not found for block '{block['label']}': {pattern} in {files_str}")
                else:
                    # Single pattern
                    result = self._find_pattern_in_files(
                        log_dir, block["file"], pattern, temp_timestamp)
                    if result:
                        pattern_found = True
                        last_result = result
                        temp_timestamp = result[0]
                    else:
                        files_str = ', '.join(block["file"]) if isinstance(block["file"], list) else block["file"]
                        get_logger().log_info(f"Pattern not found for block '{block['label']}': '{pattern}' in {files_str}")
                
                if not pattern_found:
                    return None
            
            return last_result
        
        def output_result(block: Dict, timestamp: datetime, log_line: str, 
                        filename: str) -> None:
            """Generate output for a successful match."""
            nonlocal first_timestamp, prev_timestamp
            
            if first_timestamp is None:
                first_timestamp = timestamp
                cumulative = 0.0
                delta = 0.0
            else:
                delta = (timestamp - prev_timestamp).total_seconds()
                cumulative = (timestamp - first_timestamp).total_seconds()
            
            results.append({
                "label": block["label"],
                "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
                "cumulative_seconds": cumulative,
                "delta_seconds": delta,
                "delta_formatted": self._format_duration(delta),
                "log_line": log_line[:max_log_length],
                "filename": filename
            })
            
            prev_timestamp = timestamp
        
        # Process each block
        for block in blocks:
            if not block.get("file") or not block.get("patterns"):
                continue
            
            # Try queued blocks first
            resolved_queue = []
            for queued_block in pending_queue:
                after_timestamp = prev_timestamp - timedelta(seconds=time_tolerance) if prev_timestamp else None
                result = try_block(queued_block, after_timestamp)
                if result:
                    timestamp, log_line, filename = result
                    output_result(queued_block, timestamp, log_line, filename)
                    resolved_queue.append(queued_block)
            
            # Remove resolved blocks from queue
            for resolved in resolved_queue:
                pending_queue.remove(resolved)
            
            # Try current block
            after_timestamp = prev_timestamp - timedelta(seconds=time_tolerance) if prev_timestamp else None
            result = try_block(block, after_timestamp)
            if result:
                timestamp, log_line, filename = result
                output_result(block, timestamp, log_line, filename)
            else:
                # Pattern not found
                files_str = ', '.join(block["file"]) if isinstance(block["file"], list) else block["file"]
                patterns_str = ', '.join([str(p) for p in block["patterns"]])
                if block.get("optional", False):
                    get_logger().log_info(f"⚠️ Optional block '{block['label']}' skipped - patterns not found: {patterns_str} in {files_str}")
                else:
                    # Queue for retry
                    pending_queue.append(block)
                    get_logger().log_info(f"⏳ Queuing block '{block['label']}' for retry - patterns: {patterns_str} in {files_str}")
        
        # Handle remaining queued blocks
        for queued_block in pending_queue:
            files_str = ', '.join(queued_block["file"]) if isinstance(queued_block["file"], list) else queued_block["file"]
            patterns_str = ', '.join([str(p) for p in queued_block["patterns"]])
            if not queued_block.get("optional", False):
                get_logger().log_error(f"❌ Required block '{queued_block['label']}' failed - patterns not found: {patterns_str} in {files_str}")
        
        return results

    def _find_pattern_in_files(self, log_dir: str, file_spec: Any, pattern: str,
                              after_timestamp: Optional[datetime]) -> Optional[tuple]:
        """
        Find pattern in files with chronological ordering.

        Args:
            log_dir: Directory containing log files
            file_spec: Single filename or list of filenames
            pattern: Pattern to search for
            after_timestamp: Start time for filtering

        Returns:
            (timestamp, log_line, filename) or None if not found

        """
        # Handle single filename or list
        if isinstance(file_spec, str):
            filenames = [file_spec]
        else:
            filenames = file_spec
        
        # Expand wildcards
        expanded_files = []
        for filename in filenames:
            if "*" in filename:
                expanded_files.extend(self._expand_log_files_sorted(log_dir, filename))
            else:
                expanded_files.append(filename)
        
        # Search in each file
        for filename in expanded_files:
            result = self._search_pattern_in_file_after_time(
                log_dir, filename, pattern, after_timestamp)
            if result:
                return result
        
        return None

    def _expand_log_files_sorted(self, log_dir: str, pattern: str) -> List[str]:
        """
        Expand wildcard pattern to actual filenames, sorted by modification time.

        Args:
            log_dir (str): Directory containing log files
            pattern (str): File pattern with wildcards

        Returns:
            List[str]: List of matching filenames sorted newest first

        """
        # Use SSH to get file list sorted by time (newest first)
        cmd = f"ls -1t {log_dir}/{pattern} 2>/dev/null | head -10 || true"
        result = self.ssh_connection.send(cmd)
        
        if result and result[0].strip():
            files = []
            for line in result:
                if line.strip():
                    filename = os.path.basename(line.strip())
                    if filename:
                        files.append(filename)
            get_logger().log_info(f"Expanded '{pattern}' to {len(files)} files: {files[:3]}...")
            return files
        
        # Fallback to base pattern without wildcard
        base_file = pattern.replace("*", "")
        get_logger().log_info(f"No files found for '{pattern}', trying '{base_file}'")
        return [base_file]

    def _search_pattern_in_file_after_time(self, log_dir: str, filename: str, pattern: str,
                                         start_time: Optional[datetime]) -> Optional[tuple]:
        """
        Search for pattern in file after a specific time.

        Args:
            log_dir: Directory containing log files
            filename: Name of the log file
            pattern: Pattern to search for
            start_time: Start time for filtering

        Returns:
            (timestamp, log_line, filename) or None if not found

        """
        filepath = f"{log_dir}/{filename}"
        
        # Check if file exists
        check_cmd = f"test -f {filepath} && echo 'exists' || echo 'missing'"
        check_result = self.ssh_connection.send(check_cmd)
        
        if not check_result or "missing" in check_result[0]:
            return None

        # Search for pattern with timestamp filtering
        if start_time:
            time_filter = start_time.strftime("%Y-%m-%d %H:%M:%S")
            # Use awk to filter by timestamp, then grep for pattern
            grep_cmd = f"sudo awk '$0 > \"{time_filter}\"' {filepath} 2>/dev/null | grep -F '{pattern}' | head -1"
        else:
            # Just search for pattern and get first occurrence
            grep_cmd = f"sudo grep -F '{pattern}' {filepath} 2>/dev/null | head -1"
            
        result = self.ssh_connection.send(grep_cmd)
        
        if result and result[0].strip():
            log_line = result[0].strip()
            timestamp = self._parse_timestamp(log_line)
            
            if timestamp:
                if not start_time or timestamp > start_time:
                    get_logger().log_info(f"Found '{pattern[:50]}...' at {timestamp.strftime('%Y-%m-%dT%H:%M:%S')} in {filename}")
                    return timestamp, log_line, filename

        return None

    def _parse_timestamp(self, line: str) -> Optional[datetime]:
        """
        Parse timestamp from log line supporting sysinv and ISO formats.

        Args:
            line: Log line containing timestamp

        Returns:
            Parsed timestamp or None if not found

        """
        # Parse sysinv format: "sysinv YYYY-MM-DD HH:MM:SS.fff"
        if line.startswith('sysinv '):
            match = re.search(r'sysinv (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
            if match:
                try:
                    return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    pass

        # Parse ISO format: "YYYY-MM-DDTHH:MM:SS.fff"
        match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3})', line)
        if match:
            try:
                return datetime.fromisoformat(match.group(1))
            except ValueError:
                pass
        
        # Parse standard format: "YYYY-MM-DD HH:MM:SS.fff"
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})', line)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S.%f')
            except ValueError:
                pass

        return None

    def _format_duration(self, seconds: float) -> str:
        """
        Format duration in seconds to HH:MM:SS.xxx format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string

        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def display_timing_table(self, results: Dict) -> None:
        """
        Display timing results in a formatted table.

        Args:
            results: Results from pattern analysis

        """
        if not results.get("results"):
            get_logger().log_info("\n" + "="*100)
            get_logger().log_info("UNLOCK TIMING ANALYSIS RESULTS")
            get_logger().log_info("="*100)
            get_logger().log_info("No timing results found - patterns may not exist in logs or may be outside time window")
            get_logger().log_info("Check log files and patterns for troubleshooting")
            get_logger().log_info("="*100)
            return

        # Print header
        header = "Cumulative(s)  Delta(HH:MM:SS)  Block Label                Log File      Log Line"
        separator = "-------------  ---------------  -------------------------  ------------  --------"
        
        get_logger().log_info("\n" + "="*100)
        get_logger().log_info("UNLOCK TIMING ANALYSIS RESULTS")
        get_logger().log_info("="*100)
        get_logger().log_info(header)
        get_logger().log_info(separator)

        # Print each result
        for result in results["results"]:
            cumulative = f"{result['cumulative_seconds']:8.3f}"
            delta = f"{result['delta_formatted']:>15}"
            label = f"{result['label']:<25}"
            filename = f"{result['filename']:<12}"
            log_line = result['log_line']
            
            line = f"{cumulative}  {delta}  {label}  {filename}  {log_line}"
            get_logger().log_info(line)

        # Print summary
        total_time = results["results"][-1]["cumulative_seconds"] if results["results"] else 0
        get_logger().log_info(separator)
        get_logger().log_info(f"Total patterns found: {results['total_patterns']}")
        get_logger().log_info(f"Total unlock time: {self._format_duration(total_time)}")
        get_logger().log_info("="*100)
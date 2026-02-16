"""
Grid Log Monitor
Monitors GridLog.csv for ERROR, WARNING, and ATTENTION entries
Uses seek-based reading for efficiency (no file reopening)
"""
import os
import logging
from datetime import datetime
from typing import Optional, List, Tuple
from pathlib import Path


class GridLogMonitor:
    """
    Monitors GridLog.csv file for errors using efficient seek-based reading
    
    File Location: C:\\Program Files (x86)\\Stoxxo\\Logs\\{today}\\GridLog.csv
    """
    
    def __init__(self, base_log_path: str = r"C:\Program Files (x86)\Stoxxo\Logs"):
        """
        Initialize grid log monitor
        
        Args:
            base_log_path: Base path to Stoxxo logs directory
        """
        self.base_log_path = base_log_path
        self.logger = logging.getLogger(__name__)
        
        # File tracking
        self._file_handle = None
        self._current_file_path = None
        self._last_position = 0
        self._last_check_date = None
        
        # Valid alert types
        self.valid_types = ['ATTENTION', 'ERROR', 'WARNING']
    
    def _get_today_log_path(self) -> str:
        """
        Get today's log file path
        
        Returns:
            str: Full path to today's GridLog.csv
        """
        today = datetime.now().strftime("%Y%m%d")
        log_path = os.path.join(self.base_log_path, today, "GridLog.csv")
        return log_path
    
    def _open_log_file(self) -> bool:
        """
        Open log file for reading
        
        Returns:
            bool: True if opened successfully
        """
        try:
            log_path = self._get_today_log_path()
            
            # Check if date changed (new day = new file)
            if self._current_file_path != log_path:
                self._close_file()
                self._current_file_path = log_path
                self._last_position = 0
            
            # Check if file exists
            if not os.path.exists(log_path):
                self.logger.debug(f"Log file not found: {log_path}")
                return False
            
            # Open file if not already open
            if self._file_handle is None or self._file_handle.closed:
                self._file_handle = open(log_path, 'r', encoding='utf-8', errors='replace')
                # Seek to last known position
                self._file_handle.seek(self._last_position)
                self.logger.debug(f"Opened log file: {log_path} at position {self._last_position}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error opening log file: {e}")
            return False
    
    def _close_file(self):
        """Close the current file handle"""
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()
            self.logger.debug("Closed log file")
    
    def check_for_new_entries(self, enabled_types: List[str], 
                              filter_keywords: List[str]) -> List[Tuple[str, str, str, str, str]]:
        """
        Check for new log entries
        
        Args:
            enabled_types: List of enabled alert types ['ATTENTION', 'ERROR', 'WARNING']
            filter_keywords: List of keywords to skip (comma-separated)
            
        Returns:
            List of tuples: (type, timestamp, user, strategy_tag, portfolio_name, issue)
        """
        alerts = []
        
        try:
            # Open or reopen file if needed
            if not self._open_log_file():
                return alerts
            
            # Read new lines from current position
            while True:
                line = self._file_handle.readline()
                
                if not line:
                    # End of file reached
                    break
                
                # Parse line
                alert = self._parse_log_line(line, enabled_types, filter_keywords)
                if alert:
                    alerts.append(alert)
            
            # Update position for next check
            self._last_position = self._file_handle.tell()
            
        except Exception as e:
            self.logger.error(f"Error checking log entries: {e}")
        
        return alerts
    
    def _parse_log_line(self, line: str, enabled_types: List[str], 
                       filter_keywords: List[str]) -> Optional[Tuple[str, str, str, str, str, str]]:
        """
        Parse a single log line
        
        CSV Format:
        Timestamp, Type, User, Strategy Tag, Portfolio Name, Issue
        
        Example:
        09:43:28:759,ERROR,USER1,5,SHORT5 COPY3,Strategy Tag: 5 not found!
        
        Args:
            line: Log line to parse
            enabled_types: Enabled alert types
            filter_keywords: Keywords to skip
            
        Returns:
            Tuple or None: (type, timestamp, user, strategy_tag, portfolio_name, issue)
        """
        try:
            # Remove whitespace
            line = line.strip()
            if not line:
                return None
            
            # Split CSV
            parts = [p.strip() for p in line.split(',')]
            
            if len(parts) < 6:
                return None
            
            timestamp = parts[0]
            alert_type = parts[1].upper()
            user = parts[2]
            strategy_tag = parts[3]
            portfolio_name = parts[4]
            issue = ','.join(parts[5:])  # Issue might contain commas
            
            # Check if type is enabled
            if alert_type not in enabled_types:
                return None
            
            # Check filter keywords
            if filter_keywords:
                line_lower = line.lower()
                for keyword in filter_keywords:
                    if keyword.lower() in line_lower:
                        # Keyword found, skip this alert
                        self.logger.debug(f"Filtered out alert containing: {keyword}")
                        return None
            
            return (alert_type, timestamp, user, strategy_tag, portfolio_name, issue)
            
        except Exception as e:
            self.logger.error(f"Error parsing log line: {e}")
            return None
    
    def format_alert_message(self, alert_type: str, timestamp: str, user: str, 
                            strategy_tag: str, portfolio_name: str, issue: str) -> str:
        """
        Format alert as Telegram message
        
        Args:
            alert_type: ERROR, WARNING, or ATTENTION
            timestamp: Time from log
            user: User ID or alias
            strategy_tag: Strategy tag number
            portfolio_name: Portfolio name
            issue: Issue description
            
        Returns:
            str: Formatted message
        """
        # Choose emoji based on type
        emoji_map = {
            'ERROR': '🚨',
            'WARNING': '⚡️',
            'ATTENTION': '⚠️'
        }
        emoji = emoji_map.get(alert_type, '📋')
        
        # Format message
        message = f"{emoji} {alert_type} @ {timestamp}\n"
        
        if user:
            message += f"User: {user}\n"
        
        if strategy_tag:
            message += f"Strategy tag: {strategy_tag}\n"
        
        if portfolio_name:
            message += f"Portfolio Name: {portfolio_name}\n"
        
        message += f"Issue: {issue}"
        
        return message
    
    def close(self):
        """Clean up resources"""
        self._close_file()
        self.logger.info("Grid log monitor closed")
    
    def get_status(self) -> dict:
        """
        Get current monitor status
        
        Returns:
            dict: Status information
        """
        return {
            'log_path': self._current_file_path,
            'file_open': self._file_handle is not None and not self._file_handle.closed,
            'position': self._last_position,
            'file_exists': os.path.exists(self._current_file_path) if self._current_file_path else False
        }


# Example usage
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create monitor
    monitor = GridLogMonitor()
    
    # Check for new entries
    enabled_types = ['ERROR', 'WARNING', 'ATTENTION']
    filter_keywords = ['ConnectionTimeout', 'NetworkError']
    
    alerts = monitor.check_for_new_entries(enabled_types, filter_keywords)
    
    for alert in alerts:
        alert_type, timestamp, user, strategy_tag, portfolio_name, issue = alert
        message = monitor.format_alert_message(alert_type, timestamp, user, 
                                              strategy_tag, portfolio_name, issue)
        print(message)
        print("-" * 40)
    
    # Get status
    status = monitor.get_status()
    print(f"Status: {status}")
    
    # Close
    monitor.close()
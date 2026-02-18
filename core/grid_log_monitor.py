"""
Grid Log Monitor
Monitors GridLog.csv for ERROR, WARNING, and ATTENTION entries
Uses seek-based reading for efficiency (no file reopening)

CSV Format:
Timestamp,Log Type,Message,UserID,Strategy Tag,Option Portfolio

Key parsing challenge:
- The Message field often contains commas (e.g. "Reason: X, Available: Y")
- ATTENTION entries sometimes have a second continuation line:
    "No Action Required from User!."
  which is NOT a valid CSV row — it must be skipped gracefully
- Strategy Tag and Option Portfolio are the LAST two fields (after UserID)
  We always split from the right to handle commas inside Message correctly.

Correct split strategy:
  parts = line.split(',')
  portfolio  = parts[-1]
  strat_tag  = parts[-2]
  user_id    = parts[-3]
  message    = ','.join(parts[2 : len(parts)-3])
"""
import os
import re
import logging
from datetime import datetime
from typing import Optional, List, Tuple


class GridLogMonitor:
    """
    Monitors GridLog.csv file for errors using efficient seek-based reading

    File Location: C:\\Program Files (x86)\\Stoxxo\\Logs\\{today}\\GridLog.csv
    """

    def __init__(self, base_log_path: str = r"C:\Program Files (x86)\Stoxxo\Logs"):
        self.base_log_path = base_log_path
        self.logger = logging.getLogger(__name__)

        # File tracking
        self._file_handle = None
        self._current_file_path = None
        self._last_position = 0

        # Valid alert types
        self.valid_types = ['ATTENTION', 'ERROR', 'WARNING']

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def _get_today_log_path(self) -> str:
        today = datetime.now().strftime("%d-%b-%Y")
        return os.path.join(self.base_log_path, today, "GridLog.csv")

    def _open_log_file(self) -> bool:
        try:
            log_path = self._get_today_log_path()

            # New day -> new file
            if self._current_file_path != log_path:
                self._close_file()
                self._current_file_path = log_path
                self._last_position = 0

            if not os.path.exists(log_path):
                self.logger.debug("Log file not found: %s", log_path)
                return False

            if self._file_handle is None or self._file_handle.closed:
                self._file_handle = open(log_path, 'r', encoding='utf-8', errors='replace')

                if self._last_position == 0:
                    # First open - jump to end to only catch NEW entries
                    self._file_handle.seek(0, 2)
                    self._last_position = self._file_handle.tell()
                    self.logger.debug("Opened log, skipped to end at pos %d", self._last_position)
                else:
                    self._file_handle.seek(self._last_position)

            return True

        except Exception as e:
            self.logger.error("Error opening log file: %s", e)
            return False

    def _close_file(self):
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_for_new_entries(self,
                              enabled_types: List[str],
                              filter_keywords: List[str]
                              ) -> List[Tuple[str, str, str, str, str, str]]:
        """
        Read any new lines from the log file and return parsed alerts.

        Returns list of tuples:
            (alert_type, timestamp, message, user_id, strategy_tag, portfolio_name)

        Multi-line ATTENTION handling:
        Many ATTENTION entries span 3 physical lines in the CSV:

          Line 1:  13:12:30:508,ATTENTION,<message text>
          Line 2:  (blank)
          Line 3:  No Action Required from User!.,<UserID>,<Strategy>,<Portfolio>

        The timestamp/type/message are on line 1, but UserID/Strategy/Portfolio
        are on line 3. We detect this pattern by checking if line 1 has only
        3 parts (no trailing fields), then peek ahead to grab line 3.
        """
        alerts = []

        try:
            if not self._open_log_file():
                return alerts

            pending_partial = None  # Holds a line-1 ATTENTION that needs its line-3 fields

            while True:
                line = self._file_handle.readline()
                if not line:
                    break

                stripped = line.strip()

                # ── Handle pending partial ATTENTION ───────────────────
                if pending_partial is not None:
                    if stripped == "":
                        # This is the blank line between line 1 and line 3 — skip it
                        continue

                    # This should be the "No Action Required..." continuation line
                    # Join it with the pending partial to form a complete CSV row
                    if stripped.startswith("No Action Required"):
                        # Strip the leading sentence and keep only the trailing CSV fields
                        # Format: "No Action Required from User!.,UserID,Strategy,Portfolio"
                        # We need the last 3 comma-separated values
                        cont_parts = stripped.split(',')
                        if len(cont_parts) >= 4:
                            # last 3 parts are user_id, strategy, portfolio
                            suffix = ','.join(cont_parts[-3:])
                            combined = pending_partial.rstrip() + ',' + suffix
                            pending_partial = None
                            alert = self._parse_log_line(combined, enabled_types, filter_keywords)
                            if alert:
                                alerts.append(alert)
                            continue
                        else:
                            # Unexpected format — drop the partial
                            pending_partial = None
                            continue
                    else:
                        # Not the expected continuation — abandon partial and process normally
                        pending_partial = None
                        # Fall through to process current line normally

                # ── Normal line processing ─────────────────────────────
                if not stripped:
                    continue

                parts = stripped.split(',')
                # Detect a line-1 partial ATTENTION:
                # Exactly 3 parts → timestamp, "ATTENTION", message (no trailing fields)
                # OR more than 3 but still missing the last 3 fields (can happen if message
                # itself contains semicolons — check if part[1] is ATTENTION and total < 6)
                if (len(parts) >= 2 and
                        parts[1].strip().upper() == 'ATTENTION' and
                        len(parts) < 6):
                    # Save as pending partial; next non-blank line should be the continuation
                    pending_partial = stripped
                    continue

                alert = self._parse_log_line(stripped, enabled_types, filter_keywords)
                if alert:
                    alerts.append(alert)

            self._last_position = self._file_handle.tell()

        except Exception as e:
            self.logger.error("Error checking log entries: %s", e)

        return alerts

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _parse_log_line(self,
                        line: str,
                        enabled_types: List[str],
                        filter_keywords: List[str]
                        ) -> Optional[Tuple[str, str, str, str, str, str]]:
        """
        Parse one CSV line.

        The key insight: Message can contain many commas (order details, margin
        figures etc.) but the LAST 3 fields (UserID, StrategyTag, Portfolio)
        are reliably clean. So we always split from the RIGHT.

        Minimum valid row: 6 parts  [ts, type, msg, user, strat, portfolio]
        Continuation lines like "No Action Required from User!." have fewer
        parts and are silently skipped.
        """
        try:
            line = line.strip()
            if not line:
                return None

            parts = line.split(',')

            # Need at least 6 parts for a valid CSV row
            if len(parts) < 6:
                return None

            timestamp  = parts[0].strip()
            alert_type = parts[1].strip().upper()

            # Validate alert type early (also skips the header row)
            if alert_type not in self.valid_types:
                return None

            # Always reconstruct from the right to handle commas in message
            portfolio_name = parts[-1].strip()
            strategy_tag   = parts[-2].strip()
            user_id        = parts[-3].strip()
            # Everything between column index 2 and -3 is the message
            message = ','.join(parts[2:len(parts) - 3]).strip()

            # Skip if this alert type is not enabled
            if alert_type not in enabled_types:
                return None

            # Skip if any filter keyword appears anywhere in the line
            if filter_keywords:
                line_lower = line.lower()
                for keyword in filter_keywords:
                    if keyword.strip().lower() in line_lower:
                        self.logger.debug("Filtered alert containing: %s", keyword)
                        return None

            return (alert_type, timestamp, message, user_id, strategy_tag, portfolio_name)

        except Exception as e:
            self.logger.error("Error parsing log line: %s", e)
            return None

    # ------------------------------------------------------------------
    # Message shortening
    # ------------------------------------------------------------------

    def _shorten_issue(self, message: str) -> str:
        """
        Produce a concise, human-readable issue description from the raw CSV message.
        """
        msg = message.strip()

        # Pattern: Strategy Tag not found
        if "Strategy Tag:" in msg and "not found" in msg:
            m = re.search(r'Strategy Tag[:\s]+(\S+)', msg)
            tag = m.group(1) if m else "unknown"
            m2 = re.search(r'Option Portfolio (.+?) Execution Stopped', msg)
            portfolio = f" | Portfolio: {m2.group(1).strip()}" if m2 else ""
            return f"Strategy Tag {tag} not found{portfolio} — Execution Stopped"

        # Pattern: Order Rejected and Retrying
        if "Order Rejected and Retrying" in msg:
            retry_match = re.search(r'Retrying in (\d+) Seconds', msg)
            retry_secs = retry_match.group(1) if retry_match else "?"

            leg_match = re.search(r'Leg ID[:\s]+(\S+)', msg)
            leg_id = leg_match.group(1).rstrip(';') if leg_match else ""

            if "Margin Exceeds" in msg or "Margin Shortfall" in msg:
                # Handles both "Margin Shortfall[18704.22]" and "Margin Shortfall:INR 605013.51"
                shortfall_match = re.search(r'Margin Shortfall[:\[\s]+(?:INR\s*)?([\d.]+)', msg)
                if shortfall_match:
                    shortfall = f" ₹{float(shortfall_match.group(1)):,.0f}"
                else:
                    shortfall = ""
                reason = f"Insufficient Margin (Shortfall{shortfall})"
            else:
                reason_match = re.search(r'Reason[:\s]+(.{0,80})', msg)
                reason = reason_match.group(1).strip().rstrip('.') if reason_match else "Unknown"

            result_parts = [f"Order Rejected — {reason}"]
            if leg_id:
                result_parts.append(f"Leg ID: {leg_id}")
            result_parts.append(f"Auto-retrying in {retry_secs}s")
            return "\n".join(result_parts)

        # Pattern: Order REJECTED (final, no more retries)
        if "Order REJECTED" in msg:
            leg_match = re.search(r'Leg ID[:\s]+(\S+)', msg)
            leg_id = leg_match.group(1).rstrip(';') if leg_match else ""

            if "Margin Shortfall" in msg:
                shortfall_match = re.search(r'Margin Shortfall[:\[\s]+(?:INR\s*)?([\d.]+)', msg)
                shortfall = f" ₹{float(shortfall_match.group(1)):,.0f}" if shortfall_match else ""
                reason = f"Insufficient Margin (Shortfall{shortfall})"
            else:
                reason_match = re.search(r'Reason[:\s]+(.{0,80})', msg)
                reason = reason_match.group(1).strip().rstrip('.') if reason_match else "Unknown"

            result_parts = [f"Order REJECTED (Final) — {reason}"]
            if leg_id:
                result_parts.append(f"Leg ID: {leg_id}")
            return "\n".join(result_parts)

        # Pattern: Already under Exit Execution
        if "already under Exit Execution" in msg:
            return "Portfolio already under exit execution — no action needed"

        # Pattern: Broker Feed Disconnected
        if "Broker Feed Disconnected" in msg or "feed disconnected" in msg.lower():
            return "Broker feed disconnected — attempting reconnect"

        # Pattern: Execution Stopped
        if "Execution Stopped" in msg:
            m = re.search(r'Option Portfolio (.+?) Execution Stopped', msg)
            portfolio = f" '{m.group(1).strip()}'" if m else ""
            return f"Portfolio{portfolio} execution stopped"

        # Fallback: truncate cleanly at word boundary
        if len(msg) > 200:
            truncated = msg[:197]
            last_space = truncated.rfind(' ')
            if last_space > 150:
                truncated = truncated[:last_space]
            return truncated + "..."

        return msg

    # ------------------------------------------------------------------
    # Telegram message formatting
    # ------------------------------------------------------------------

    def format_alert_message(self,
                             alert_type: str,
                             timestamp: str,
                             message: str,
                             user_id: str,
                             user_alias: str,
                             strategy_tag: str,
                             portfolio_name: str) -> str:
        """
        Format alert as a clean Telegram message.

        Example output:
        ⚠️ ATTENTION @ 13:48:12
        User: RKJ34 (KAMBALA)
        Strategy: RF-20-3P5-NIFTY-30S-JR
        Portfolio: HTTP_SHORT11_7
        Issue: Order Rejected — Insufficient Margin (Shortfall ₹18,704)
               Leg ID: 5371
               Auto-retrying in 4s
        """
        emoji_map = {
            'ERROR':     '🚨',
            'WARNING':   '⚡️',
            'ATTENTION': '⚠️',
        }
        emoji = emoji_map.get(alert_type, '📋')

        # Trim milliseconds from timestamp for readability: 13:48:12:331 -> 13:48:12
        display_time = timestamp.rsplit(':', 1)[0] if timestamp.count(':') == 3 else timestamp

        short_issue = self._shorten_issue(message)

        lines = [f"{emoji} {alert_type} @ {display_time}"]

        if user_id and user_alias:
            lines.append(f"User: {user_id} ({user_alias})")
        elif user_id:
            lines.append(f"User: {user_id}")
        elif user_alias:
            lines.append(f"User: {user_alias}")

        if strategy_tag:
            lines.append(f"Strategy: {strategy_tag}")
        if portfolio_name:
            lines.append(f"Portfolio: {portfolio_name}")

        lines.append(f"Issue: {short_issue}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        self._close_file()
        self.logger.info("Grid log monitor closed")

    def get_status(self) -> dict:
        return {
            'log_path':    self._current_file_path,
            'file_open':   self._file_handle is not None and not self._file_handle.closed,
            'position':    self._last_position,
            'file_exists': os.path.exists(self._current_file_path) if self._current_file_path else False,
        }
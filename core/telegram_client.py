"""
Telegram Client
Intelligent message sending with burst deduplication, buffering, and background drain.

Architecture:
  Alert fires -> TelegramClientSync.send_message(text)
       |
  BurstBuffer (4s window)
    - Groups identical alert type+user combinations
    - Deduplicates: 50 same alerts -> 1 summary with count + time range
       |  (after buffer window expires)
  queue.Queue
       |
  SenderThread (runs independently, always draining)
    - Respects Telegram rate limit (18 per 58s)
    - If over limit: waits for window to roll, combines backlog if >5 pile up
    - Never blocks the alert service thread

Key improvements over original:
  1. Burst deduplication  -- 50 identical margin errors -> 1 smart summary
  2. Auto-draining        -- sender thread runs continuously, no trigger needed
  3. Non-blocking         -- alert service just buffers and returns immediately
  4. Intelligent grouping -- groups by (alert header + user line) fingerprint
"""

import queue
import re
import threading
import time
import logging
import asyncio
from collections import deque, defaultdict
from datetime import datetime
from typing import Optional
import aiohttp


# ---------------------------------------------------------------------------
# Burst buffer
# ---------------------------------------------------------------------------

class BurstBuffer:
    """
    Adaptive burst buffer — flushes when messages stop arriving, not after
    a fixed wait.

    Two-timer strategy:
      SILENCE_SECONDS (0.2s) — reset on every new message for a fingerprint.
            If no new message arrives within this window for any group,
            flush immediately. Catches a burst that finishes quickly.

      MAX_WAIT_SECONDS (2.0s) — hard cap from the first message.
            Even if messages keep trickling in, always flush by this deadline.
            Prevents indefinite delay if alerts arrive slowly and continuously.

    Real-world result for your scenario:
      - 5 alerts per user arrive in ~300ms  → flush at ~500ms (300 + 200ms silence)
      - Alerts trickle slowly over 3 seconds → flush at 2.0s (hard cap)
      - Single isolated alert               → flush at 200ms (silence detected fast)
    """

    SILENCE_SECONDS  = 0.2   # flush this long after last message
    MAX_WAIT_SECONDS = 2.0   # never wait longer than this from first message

    def __init__(self):
        self._lock          = threading.Lock()
        self._groups        = defaultdict(list)   # fingerprint -> [(timestamp, message)]
        self._silence_timer = None   # resets on every new message
        self._max_timer     = None   # set once on first message, never reset
        self._on_flush      = None
        self.logger         = logging.getLogger(__name__)

    def set_flush_callback(self, callback):
        self._on_flush = callback

    def add(self, message: str):
        fingerprint = self._fingerprint(message)
        with self._lock:
            self._groups[fingerprint].append((time.time(), message))

            # Silence timer — reset on every new message
            if self._silence_timer is not None:
                self._silence_timer.cancel()
            self._silence_timer = threading.Timer(self.SILENCE_SECONDS, self._flush)
            self._silence_timer.daemon = True
            self._silence_timer.start()

            # Max-wait timer — start once, never reset
            if self._max_timer is None:
                self._max_timer = threading.Timer(self.MAX_WAIT_SECONDS, self._flush)
                self._max_timer.daemon = True
                self._max_timer.start()

    def _fingerprint(self, message: str) -> str:
        """
        Group by alert_type + user only — NOT portfolio.

        This means 5 alerts for the same user across different portfolios
        all collapse into one per-user summary, which is the correct
        behaviour for the trading scenario where margin shortfalls hit
        multiple portfolios of the same user simultaneously.

        Structure of a grid log message:
          line 0: "⚠️ ATTENTION @ 13:12:30"   ← strip timestamp
          line 1: "User: FZ20267 (SUNNY)"      ← always present for grid alerts
          line 2: "Strategy: ..."
          line 3: "Portfolio: ..."              ← intentionally excluded
          line 4: "Issue: ..."

        For position alerts (MTM/Margin/Quantity):
          line 0: "📈 MTM ALERT"
          line 1: "User Alias: Simulated1"
          → same logic, groups by alert type + user alias

        Different users → different fingerprints → separate messages.
        Different alert types (ATTENTION vs ERROR) → separate messages.
        """
        lines = [l.strip() for l in message.splitlines() if l.strip()]

        # Line 0: alert type header (strip timestamp)
        header = re.sub(r'\s*@\s*[\d:]+', '', lines[0]).strip() if lines else ''

        # Line 1: user identifier (User: X or User Alias: X)
        user = lines[1].strip() if len(lines) > 1 else ''

        return f"{header} | {user}"

    def _extract_portfolio_line(self, message: str) -> str:
        """Extract the Portfolio line from a message, or empty string."""
        for line in message.splitlines():
            stripped = line.strip()
            if stripped.startswith('Portfolio:'):
                return stripped[len('Portfolio:'):].strip()
        return ''

    def _extract_field(self, message: str, prefix: str) -> str:
        """Extract value of a named field from a message, e.g. 'Issue:' -> value."""
        for line in message.splitlines():
            s = line.strip()
            if s.startswith(prefix):
                return s[len(prefix):].strip()
        return ''

    def _build_bullet(self, message: str) -> str:
        """
        Build a full-detail bullet block for one entry inside a burst summary.

        Grid log alerts (have Issue: field):
            • HTTP_SHORT11 — Order Rejected — Insufficient Margin (Shortfall ₹605,000)

        Position alerts (have Metric: / Threshold: / Actual:):
            • Puts Net Quantity
              Threshold: 1  |  Actual: 3

        Falls back gracefully if neither structure matches.
        """
        portfolio = self._extract_field(message, 'Portfolio:')
        issue     = self._extract_field(message, 'Issue:')
        metric    = self._extract_field(message, 'Metric:')
        threshold = self._extract_field(message, 'Threshold:')
        actual    = self._extract_field(message, 'Actual:')

        if issue:
            # Grid log alert — single line with portfolio prefix
            if portfolio:
                return f"  • {portfolio}  —  {issue}"
            return f"  • {issue}"

        if metric:
            # Position alert — metric on bullet, threshold+actual as sub-line
            detail = f"  • {metric}"
            if threshold and actual:
                detail += f"\n      Threshold: {threshold}  |  Actual: {actual}"
            elif threshold:
                detail += f"\n      Threshold: {threshold}"
            return detail

        # Fallback — just use last meaningful line
        lines = [l.strip() for l in message.splitlines() if l.strip()]
        return f"  • {lines[-1]}" if lines else "  • (no detail)"

    def _extract_timestamp(self, message: str) -> str:
        """Extract the timestamp from the header line."""
        first_line = message.splitlines()[0] if message else ''
        m = re.search(r'@\s*([\d:]+)', first_line)
        return m.group(1) if m else ''

    def _flush(self):
        with self._lock:
            # Guard against double-flush (both timers can fire close together)
            if not self._groups:
                return
            groups = dict(self._groups)
            self._groups.clear()
            if self._silence_timer is not None:
                self._silence_timer.cancel()
                self._silence_timer = None
            if self._max_timer is not None:
                self._max_timer.cancel()
                self._max_timer = None

        if not self._on_flush:
            return

        messages_to_send = []
        for fingerprint, entries in groups.items():
            count = len(entries)
            if count == 1:
                messages_to_send.append(entries[0][1])
            else:
                messages_to_send.append(self._build_summary(entries, count))

        self._on_flush(messages_to_send)

    def _build_summary(self, entries: list, count: int) -> str:
        """
        Collapse N alerts for the same user into one per-user summary.
        Each affected portfolio gets its own bullet line.

        Example output (5 alerts, same user, different portfolios):

        ⚠️ ATTENTION — 5 alerts @ 13:12:30–13:12:34
        User: FZ20267 (SUNNY)
        ─────────────────────────────────
        • TEST ATTENTION  — Order Rejected — Insufficient Margin (Shortfall ₹605,000)
        • HTTP_SHORT11    — Order Rejected — Insufficient Margin (Shortfall ₹412,000)
        • HTTP_LONG12     — Order Rejected — Insufficient Margin (Shortfall ₹318,000)
        • SHORT5_COPY     — Strategy Tag 4 not found — Execution Stopped
        • NON-DIREC       — Order Rejected — Insufficient Margin (Shortfall ₹205,000)
        """
        first_ts = entries[0][0]
        last_ts  = entries[-1][0]

        template  = entries[0][1]
        t_lines   = template.splitlines()

        # Build header: strip old timestamp, add count + time range
        header_base = re.sub(r'\s*@\s*[\d:]+', '', t_lines[0]).strip() if t_lines else ''
        first_time  = datetime.fromtimestamp(first_ts).strftime("%H:%M:%S")
        last_time   = datetime.fromtimestamp(last_ts).strftime("%H:%M:%S")
        time_range  = first_time if first_time == last_time else f"{first_time}–{last_time}"
        header      = f"{header_base} — {count} alerts @ {time_range}"

        # User line (line 1 of template)
        user_line = t_lines[1].strip() if len(t_lines) > 1 else ''

        # Build one detailed bullet per entry
        bullets = []
        for _, msg in entries:
            bullets.append(self._build_bullet(msg))

        divider = '─' * 33
        parts   = [header, user_line, divider] + bullets
        return "\n".join(parts)

    def cancel(self):
        with self._lock:
            if self._silence_timer is not None:
                self._silence_timer.cancel()
                self._silence_timer = None
            if self._max_timer is not None:
                self._max_timer.cancel()
                self._max_timer = None


# ---------------------------------------------------------------------------
# Background sender thread
# ---------------------------------------------------------------------------

class SenderThread(threading.Thread):
    """
    Daemon thread that continuously drains the send queue while
    respecting Telegram's rate limit.

    Strategy:
      - Under threshold  -> send immediately
      - At threshold     -> sleep until oldest timestamp expires, then send
      - Queue backing up (>= COMBINE_THRESHOLD while waiting)
                         -> combine everything into one message now
    """

    RATE_LIMIT_WINDOW  = 58   # seconds
    RATE_LIMIT_MAX     = 18   # messages per window
    COMBINE_THRESHOLD  = 5    # combine queue if this many back up while waiting
    POLL_INTERVAL_IDLE   = 1.0   # sleep when queue empty (low CPU)
    POLL_INTERVAL_ACTIVE = 0.05  # sleep when draining (fast throughput)

    def __init__(self, bot_token: str, channel_id: str):
        super().__init__(daemon=True)
        self.bot_token   = bot_token
        self.channel_id  = channel_id
        self.logger      = logging.getLogger(__name__)
        self._queue      = queue.Queue()
        self._stop_event = threading.Event()
        self._sent_ts    = deque()
        self._loop       = None

    def enqueue(self, message: str):
        self._queue.put(message)

    def stop(self):
        self._stop_event.set()

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self.logger.debug("Telegram sender thread started")
        try:
            while not self._stop_event.is_set():
                self._drain_once()
                # Sleep shorter when there's work to do, longer when idle
                sleep_time = self.POLL_INTERVAL_ACTIVE if not self._queue.empty() else self.POLL_INTERVAL_IDLE
                time.sleep(sleep_time)
            # Final drain
            self._drain_once()
        finally:
            self._loop.close()
            self.logger.debug("Telegram sender thread stopped")

    def _drain_once(self):
        while not self._queue.empty():
            self._clean_old_timestamps()

            if len(self._sent_ts) >= self.RATE_LIMIT_MAX:
                # Calculate how long until the oldest send expires
                wait_secs = (self._sent_ts[0] + self.RATE_LIMIT_WINDOW) - time.time()
                if wait_secs > 0:
                    if self._queue.qsize() >= self.COMBINE_THRESHOLD:
                        # Queue backing up -- combine everything now
                        self._send_combined_backlog()
                    else:
                        self.logger.debug(
                            "Rate limit (%d/%d). Waiting %.1fs",
                            len(self._sent_ts), self.RATE_LIMIT_MAX, wait_secs
                        )
                        time.sleep(min(wait_secs + 0.1, 5.0))
                    return
                continue  # timestamp just expired, recount

            try:
                message = self._queue.get_nowait()
            except queue.Empty:
                break

            if self._send_sync(message):
                self._sent_ts.append(time.time())
            else:
                self.logger.warning("Message delivery failed (Telegram unreachable)")

    def _send_combined_backlog(self):
        messages = []
        while not self._queue.empty():
            try:
                messages.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if not messages:
            return

        if len(messages) == 1:
            combined = messages[0]
        else:
            header   = f"BACKLOG COMBINED ({len(messages)} alerts)\n" + "\u2500" * 36 + "\n\n"
            combined = header + "\n\n".join(f"[{i+1}] {m}" for i, m in enumerate(messages))

        self.logger.warning("Combining %d backlogged messages", len(messages))
        if self._send_sync(combined):
            self._sent_ts.append(time.time())

    def _send_sync(self, text: str) -> bool:
        try:
            return self._loop.run_until_complete(self._send_async(text))
        except Exception as e:
            self.logger.error("Send error: %s", e)
            return False

    async def _send_async(self, text: str) -> bool:
        url     = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.channel_id, "text": text, "parse_mode": "HTML"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return True
                    error = await resp.text()
                    self.logger.error("Telegram API %d: %s", resp.status, error[:200])
                    return False
        except asyncio.TimeoutError:
            self.logger.error("Telegram request timed out")
            return False
        except Exception as e:
            self.logger.error("Telegram request failed: %s", e)
            return False

    def _clean_old_timestamps(self):
        cutoff = time.time() - self.RATE_LIMIT_WINDOW
        while self._sent_ts and self._sent_ts[0] < cutoff:
            self._sent_ts.popleft()

    def get_status(self) -> dict:
        self._clean_old_timestamps()
        return {
            "queue_size":      self._queue.qsize(),
            "sent_in_window":  len(self._sent_ts),
            "rate_limit_max":  self.RATE_LIMIT_MAX,
            "window_seconds":  self.RATE_LIMIT_WINDOW,
        }


# ---------------------------------------------------------------------------
# Public interface -- drop-in replacement for old TelegramClientSync
# ---------------------------------------------------------------------------

class TelegramClientSync:
    """
    Drop-in replacement. Same public API as before -- nothing else in the
    project needs to change.

    Internally: BurstBuffer (4s dedup window) -> SenderThread (background drain).
    send_message() is now fully non-blocking (fire-and-forget).
    """

    def __init__(self, bot_token: str, channel_id: str):
        self.bot_token      = bot_token
        self.channel_id     = channel_id
        self.logger         = logging.getLogger(__name__)
        self._bot_username  = None

        self._sender = SenderThread(bot_token, channel_id)
        self._sender.start()

        self._buffer = BurstBuffer()
        self._buffer.set_flush_callback(self._on_buffer_flush)

    def _on_buffer_flush(self, messages: list):
        for msg in messages:
            self._sender.enqueue(msg)

    def send_message(self, text: str) -> bool:
        """Non-blocking. Message goes through burst buffer (4s dedup window)."""
        self._buffer.add(text)
        return True

    def send_urgent(self, text: str) -> bool:
        """
        Non-blocking. Bypasses burst buffer — goes straight to send queue.
        Use for critical one-off alerts (ERROR, MTM breach, Margin breach)
        where immediate delivery matters more than deduplication.
        Delivers in ~200ms instead of 4s.
        """
        self._sender.enqueue(text)
        return True

    def verify_connection(self) -> tuple:
        """Silently verify credentials (getMe only, no message sent)."""
        return self._run_once(self._async_get_me())

    def test_connection(self) -> tuple:
        """Verify credentials and send a test message."""
        ok, username = self._run_once(self._async_get_me())
        if ok:
            ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            test_msg = f"Test Alert from Stoxxo Monitor\n\nConnection Successful\nTime: {ts}"
            # Bypass buffer for test message so it sends immediately
            self._sender.enqueue(test_msg)
        return ok, username

    async def _async_get_me(self) -> tuple:
        url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('ok'):
                            username = data['result'].get('username', 'Unknown')
                            self._bot_username = username
                            return True, username
            return False, None
        except Exception as e:
            self.logger.error("getMe failed: %s", e)
            return False, None

    def _run_once(self, coro):
        """Run a one-off coroutine in a temporary event loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        except Exception as e:
            self.logger.error("Async run failed: %s", e)
            return False, None
        finally:
            loop.close()

    def get_rate_limit_status(self) -> dict:
        return self._sender.get_status()

    def get_pending_count(self) -> int:
        return self._sender.get_status()["queue_size"]

    def close(self):
        self._buffer.cancel()
        self._sender.stop()
        self._sender.join(timeout=5)


# Keep old name alive in case anything imports TelegramClient directly
TelegramClient = TelegramClientSync
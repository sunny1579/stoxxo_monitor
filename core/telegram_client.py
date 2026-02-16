"""
Telegram Client
Handles sending messages to Telegram with rate limiting and queueing
"""
import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Optional
import aiohttp


class TelegramClient:
    """
    Telegram bot client with rate limiting and message queueing
    
    Rate limit: 20 messages per minute (per Telegram API limits)
    Strategy: Track last 58 seconds, combine messages if 18+ already sent
    """
    
    def __init__(self, bot_token: str, channel_id: str):
        """
        Initialize Telegram client
        
        Args:
            bot_token: Telegram bot token
            channel_id: Telegram channel ID (e.g., -1003220645575)
        """
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.message_timestamps = deque()  # Track last 58 seconds of messages
        self.rate_limit_window = 58  # seconds
        self.rate_limit_threshold = 18  # max messages before combining
        
        # Message queue
        self.pending_messages = []  # Messages waiting to be sent
        
        # Connection status
        self._last_test_result = None
        self._bot_username = None
    
    async def send_message(self, text: str) -> bool:
        """
        Send a message to Telegram channel
        Handles rate limiting automatically
        
        Args:
            text: Message text to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            # Clean old timestamps (older than 58 seconds)
            self._clean_old_timestamps()
            
            # Check rate limit
            if len(self.message_timestamps) >= self.rate_limit_threshold:
                # Rate limit exceeded, queue message
                self.logger.warning(f"Rate limit approaching ({len(self.message_timestamps)}/20), queueing message")
                self.pending_messages.append(text)
                return False
            
            # Send message
            success = await self._send_to_telegram(text)
            
            if success:
                # Record timestamp
                self.message_timestamps.append(time.time())
                self.logger.info("Message sent to Telegram successfully")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")
            return False
    
    async def send_message_with_queue(self, text: str) -> bool:
        """
        Send a message, combining with queued messages if rate limited
        
        Args:
            text: Message text to send
            
        Returns:
            bool: True if sent (either alone or combined), False if queued
        """
        self._clean_old_timestamps()
        
        # Add to pending
        self.pending_messages.append(text)
        
        # Check if we can send
        if len(self.message_timestamps) < self.rate_limit_threshold:
            # Can send individual messages
            if len(self.pending_messages) == 1:
                # Only one message, send it
                msg = self.pending_messages.pop(0)
                return await self.send_message(msg)
            else:
                # Multiple pending, send them individually (if rate allows)
                sent_count = 0
                while self.pending_messages and len(self.message_timestamps) < self.rate_limit_threshold:
                    msg = self.pending_messages.pop(0)
                    if await self.send_message(msg):
                        sent_count += 1
                return sent_count > 0
        else:
            # Rate limit reached, combine all pending messages
            if len(self.pending_messages) > 0:
                combined = self._combine_messages(self.pending_messages)
                self.pending_messages.clear()
                return await self.send_message(combined)
            return False
    
    def _combine_messages(self, messages: list) -> str:
        """
        Combine multiple messages into one
        
        Args:
            messages: List of message strings
            
        Returns:
            str: Combined message
        """
        header = f"⚠️ COMBINED ALERTS ({len(messages)} messages)\n"
        header += "=" * 40 + "\n\n"
        
        combined = header
        for i, msg in enumerate(messages, 1):
            combined += f"[{i}] {msg}\n\n"
        
        return combined
    
    def _clean_old_timestamps(self):
        """Remove timestamps older than rate limit window"""
        current_time = time.time()
        cutoff = current_time - self.rate_limit_window
        
        while self.message_timestamps and self.message_timestamps[0] < cutoff:
            self.message_timestamps.popleft()
    
    async def _send_to_telegram(self, text: str) -> bool:
        """
        Actual HTTP request to Telegram API
        
        Args:
            text: Message text
            
        Returns:
            bool: Success status
        """
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Telegram API error {response.status}: {error_text}")
                        return False
                        
        except asyncio.TimeoutError:
            self.logger.error("Telegram API request timed out")
            return False
        except Exception as e:
            self.logger.error(f"Telegram API request failed: {e}")
            return False
    
    async def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Test Telegram connection by sending a test message
        
        Returns:
            tuple: (success: bool, bot_username: Optional[str])
        """
        try:
            # Get bot info first
            url = f"https://api.telegram.org/bot{self.bot_token}/getMe"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_username = data['result'].get('username', 'Unknown')
                            self._bot_username = bot_username
                            
                            # Send test message
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            test_msg = f"✅ Test Alert from Stoxxo Monitor\n\nConnection Successful\nTime: {timestamp}"
                            
                            success = await self._send_to_telegram(test_msg)
                            self._last_test_result = success
                            
                            return success, bot_username
                        else:
                            self.logger.error(f"Telegram getMe failed: {data}")
                            return False, None
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Telegram getMe error {response.status}: {error_text}")
                        return False, None
                        
        except Exception as e:
            self.logger.error(f"Telegram connection test failed: {e}")
            return False, None
    
    def get_pending_count(self) -> int:
        """Get number of pending messages in queue"""
        return len(self.pending_messages)
    
    def get_rate_limit_status(self) -> dict:
        """
        Get current rate limit status
        
        Returns:
            dict: {messages_sent: int, window_seconds: int, threshold: int}
        """
        self._clean_old_timestamps()
        return {
            'messages_sent': len(self.message_timestamps),
            'window_seconds': self.rate_limit_window,
            'threshold': self.rate_limit_threshold,
            'pending_count': len(self.pending_messages)
        }
    
    def clear_queue(self):
        """Clear all pending messages"""
        cleared = len(self.pending_messages)
        self.pending_messages.clear()
        self.logger.info(f"Cleared {cleared} pending messages")


# Synchronous wrapper for use in Qt applications
class TelegramClientSync:
    """
    Synchronous wrapper around TelegramClient for use in Qt
    """
    
    def __init__(self, bot_token: str, channel_id: str):
        self.client = TelegramClient(bot_token, channel_id)
        self.logger = logging.getLogger(__name__)
        # Reuse event loop for better performance
        self._loop = None
    
    def _get_loop(self):
        """Get or create event loop"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop
    
    def send_message(self, text: str) -> bool:
        """Send message synchronously"""
        try:
            loop = self._get_loop()
            result = loop.run_until_complete(self.client.send_message_with_queue(text))
            return result
        except Exception as e:
            self.logger.error(f"Sync send failed: {e}")
            return False
    
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Test connection synchronously"""
        try:
            loop = self._get_loop()
            result = loop.run_until_complete(self.client.test_connection())
            return result
        except Exception as e:
            self.logger.error(f"Sync test failed: {e}")
            return False, None
    
    def get_rate_limit_status(self) -> dict:
        """Get rate limit status"""
        return self.client.get_rate_limit_status()
    
    def get_pending_count(self) -> int:
        """Get pending message count"""
        return self.client.get_pending_count()
    
    def close(self):
        """Close event loop"""
        if self._loop and not self._loop.is_closed():
            self._loop.close()
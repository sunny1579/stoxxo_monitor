"""
Alert Service
Main orchestrator that connects all alert components
Runs when ENGINE START is pressed, stops when ENGINE STOP is pressed
"""
import logging
import time
from typing import Optional, List
from PyQt6.QtCore import QThread, pyqtSignal

from core.telegram_client import TelegramClientSync
from core.grid_log_monitor import GridLogMonitor
from services.alert_checker import AlertChecker
from models.position_summary import OptionsPositionSummary


class AlertService(QThread):
    """
    Background service that monitors and sends alerts
    Runs in separate thread to avoid blocking UI
    """
    
    # Signals
    alert_sent = pyqtSignal(str, str)  # (alert_type, message)
    error_occurred = pyqtSignal(str)  # error message
    status_changed = pyqtSignal(str)  # status message
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.telegram_client: Optional[TelegramClientSync] = None
        self.grid_log_monitor: Optional[GridLogMonitor] = None
        self.alert_checker: Optional[AlertChecker] = None
        
        # Control
        self.is_running = False
        self._should_stop = False
        
        # Configuration (will be updated from UI)
        self.telegram_enabled = False
        self.bot_token = ""
        self.channel_id = ""
        self.sound_enabled = True
        
        self.grid_log_enabled = False
        self.grid_attention_enabled = True
        self.grid_error_enabled = True
        self.grid_warning_enabled = True
        self.grid_filter_enabled = False
        self.grid_filter_keywords = []
        
        self.mtm_roi_enabled = False
        self.mtm_roi_thresholds = {}
        
        self.margin_enabled = False
        self.margin_thresholds = {}
        
        self.quantity_enabled = False
        self.quantity_thresholds = {}
        
        # Current position data (updated from main window)
        self._current_summaries: List[OptionsPositionSummary] = []
        
        # Polling interval
        self.check_interval = 0.5  # seconds
    
    def update_config(self, 
                     telegram_config: dict,
                     grid_config: dict,
                     mtm_roi_config: dict,
                     margin_config: dict,
                     quantity_config: dict):
        """
        Update configuration from UI
        
        Args:
            telegram_config: {bot_token, channel_id, sound_enabled}
            grid_config: {enabled, attention, error, warning, filter_enabled, filter_keywords}
            mtm_roi_config: {enabled, thresholds}
            margin_config: {enabled, thresholds}
            quantity_config: {enabled, thresholds}
        """
        # Telegram
        self.bot_token = telegram_config.get('bot_token', '')
        self.channel_id = telegram_config.get('channel_id', '')
        self.sound_enabled = telegram_config.get('sound_enabled', True)
        self.telegram_enabled = bool(self.bot_token and self.channel_id)
        
        # Grid log
        self.grid_log_enabled = grid_config.get('enabled', False)
        self.grid_attention_enabled = grid_config.get('attention', True)
        self.grid_error_enabled = grid_config.get('error', True)
        self.grid_warning_enabled = grid_config.get('warning', True)
        self.grid_filter_enabled = grid_config.get('filter_enabled', False)
        self.grid_filter_keywords = grid_config.get('filter_keywords', [])
        
        # MTM/ROI
        self.mtm_roi_enabled = mtm_roi_config.get('enabled', False)
        self.mtm_roi_thresholds = mtm_roi_config.get('thresholds', {})
        
        # Margin
        self.margin_enabled = margin_config.get('enabled', False)
        self.margin_thresholds = margin_config.get('thresholds', {})
        
        # Quantity
        self.quantity_enabled = quantity_config.get('enabled', False)
        self.quantity_thresholds = quantity_config.get('thresholds', {})
        
        self.logger.info("Alert service configuration updated")
    
    def update_position_data(self, summaries: List[OptionsPositionSummary]):
        """
        Update current position data (called from main window on each poll)
        
        Args:
            summaries: List of OptionsPositionSummary objects
        """
        self._current_summaries = summaries
    
    def stop(self):
        """Stop the alert service"""
        self.logger.info("Stopping alert service...")
        self._should_stop = True
        self.is_running = False
    
    def run(self):
        """Main alert monitoring loop (runs in separate thread)"""
        self.logger.info("Alert service started")
        self.is_running = True
        self._should_stop = False
        
        try:
            # Initialize components
            self._init_components()
            
            # Main loop
            while not self._should_stop:
                try:
                    # Check grid log alerts
                    if self.grid_log_enabled and self.telegram_enabled:
                        self._check_grid_log_alerts()
                    
                    # Check position-based alerts
                    if self.telegram_enabled and self._current_summaries:
                        if self.mtm_roi_enabled or self.margin_enabled or self.quantity_enabled:
                            self._check_position_alerts()
                    
                    # Wait before next check
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Error in alert loop: {e}")
                    self.error_occurred.emit(str(e))
                    time.sleep(1)  # Brief pause on error
            
        except Exception as e:
            self.logger.error(f"Fatal error in alert service: {e}")
            self.error_occurred.emit(f"Alert service crashed: {e}")
        
        finally:
            self._cleanup_components()
            self.logger.info("Alert service stopped")
    
    def _init_components(self):
        """Initialize alert components"""
        try:
            # Telegram client
            if self.telegram_enabled:
                self.telegram_client = TelegramClientSync(self.bot_token, self.channel_id)
                self.logger.info("Telegram client initialized")
            
            # Grid log monitor
            if self.grid_log_enabled:
                self.grid_log_monitor = GridLogMonitor()
                self.logger.info("Grid log monitor initialized")
            
            # Alert checker
            self.alert_checker = AlertChecker()
            self.logger.info("Alert checker initialized")
            
            self.status_changed.emit("Alert service running")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            raise
    
    def _cleanup_components(self):
        """Clean up components"""
        if self.grid_log_monitor:
            self.grid_log_monitor.close()
        
        if self.telegram_client:
            self.telegram_client.close()
        
        self.status_changed.emit("Alert service stopped")
    
    def _check_grid_log_alerts(self):
        """Check for grid log errors and send alerts"""
        if not self.grid_log_monitor:
            return
        
        try:
            # Build enabled types list
            enabled_types = []
            if self.grid_attention_enabled:
                enabled_types.append('ATTENTION')
            if self.grid_error_enabled:
                enabled_types.append('ERROR')
            if self.grid_warning_enabled:
                enabled_types.append('WARNING')
            
            if not enabled_types:
                return
            
            # Get filter keywords
            filter_keywords = self.grid_filter_keywords if self.grid_filter_enabled else []
            
            # Check for new entries
            alerts = self.grid_log_monitor.check_for_new_entries(enabled_types, filter_keywords)
            
            # Send each alert
            for alert in alerts:
                alert_type, timestamp, user, strategy_tag, portfolio_name, issue = alert
                message = self.grid_log_monitor.format_alert_message(
                    alert_type, timestamp, user, strategy_tag, portfolio_name, issue
                )
                
                # Send to Telegram
                success = self.telegram_client.send_message(message)
                
                if success:
                    self.alert_sent.emit('grid_log', message)
                    self.logger.info(f"Grid log alert sent: {alert_type}")
                    
                    # Play sound if enabled
                    if self.sound_enabled:
                        self._play_alert_sound()
        
        except Exception as e:
            self.logger.error(f"Error checking grid log: {e}")
    
    def _check_position_alerts(self):
        """Check position-based alerts (MTM/ROI/Margin/Quantity)"""
        if not self.alert_checker or not self._current_summaries:
            return
        
        try:
            print(f"DEBUG AlertService: Checking alerts for {len(self._current_summaries)} users")  # DEBUG
            print(f"DEBUG AlertService: MTM enabled: {self.mtm_roi_enabled}, thresholds: {len(self.mtm_roi_thresholds)}")  # DEBUG
            print(f"DEBUG AlertService: Margin enabled: {self.margin_enabled}, thresholds: {len(self.margin_thresholds)}")  # DEBUG
            print(f"DEBUG AlertService: Quantity enabled: {self.quantity_enabled}, thresholds: {len(self.quantity_thresholds)}")  # DEBUG
            
            # Check all alerts
            alerts = self.alert_checker.check_all_alerts(
                self._current_summaries,
                self.mtm_roi_thresholds if self.mtm_roi_enabled else {},
                self.margin_thresholds if self.margin_enabled else {},
                self.quantity_thresholds if self.quantity_enabled else {}
            )
            
            print(f"DEBUG AlertService: {len(alerts)} alerts detected")  # DEBUG
            
            # Send each alert
            for alert in alerts:
                message = alert.format_message()
                print(f"DEBUG AlertService: Sending alert: {alert.alert_type} for {alert.user_alias}")  # DEBUG
                
                # Send to Telegram
                success = self.telegram_client.send_message(message)
                
                if success:
                    self.alert_sent.emit(alert.alert_type, message)
                    self.logger.info(f"Position alert sent: {alert.alert_type} for {alert.user_alias}")
                    
                    # Play sound if enabled
                    if self.sound_enabled:
                        self._play_alert_sound()
                else:
                    print(f"DEBUG AlertService: Failed to send alert")  # DEBUG
        
        except Exception as e:
            self.logger.error(f"Error checking position alerts: {e}")
            print(f"DEBUG AlertService: Exception: {e}")  # DEBUG
    
    def _play_alert_sound(self):
        """Play alert sound (if enabled)"""
        try:
            # Simple beep using system bell
            print('\a')  # ASCII bell character
        except Exception as e:
            self.logger.debug(f"Could not play sound: {e}")
    
    def get_status(self) -> dict:
        """
        Get current service status
        
        Returns:
            dict: Status information
        """
        return {
            'running': self.is_running,
            'telegram_enabled': self.telegram_enabled,
            'grid_log_enabled': self.grid_log_enabled,
            'mtm_roi_enabled': self.mtm_roi_enabled,
            'margin_enabled': self.margin_enabled,
            'quantity_enabled': self.quantity_enabled,
            'active_users': len(self._current_summaries)
        }
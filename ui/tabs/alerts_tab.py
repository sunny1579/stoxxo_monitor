"""
Alerts Tab
Contains alert configuration and monitoring
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from ui.widgets import (TelegramConfigWidget, GridAlertsWidget, 
                        MTMROIAlertsWidget, MarginAlertsWidget,
                        QuantityAlertsWidget)
from utils.settings_manager import SettingsManager
from core.telegram_client import TelegramClientSync
import logging


class TelegramVerifyThread(QThread):
    """Background thread for silently verifying Telegram credentials (no test message)"""
    result_ready = pyqtSignal(bool, str)  # success, bot_username or error

    def __init__(self, bot_token, channel_id):
        super().__init__()
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.logger = logging.getLogger(__name__)

    def run(self):
        try:
            client = TelegramClientSync(self.bot_token, self.channel_id)
            success, bot_username = client.verify_connection()
            if success and bot_username:
                self.result_ready.emit(True, bot_username)
            else:
                self.result_ready.emit(False, "Verification failed")
        except Exception as e:
            self.logger.error(f"Telegram verify error: {e}")
            self.result_ready.emit(False, str(e))


class TelegramTestThread(QThread):
    """Background thread for testing Telegram connection"""
    result_ready = pyqtSignal(bool, str)  # success, bot_username or error
    
    def __init__(self, bot_token, channel_id):
        super().__init__()
        self.bot_token = bot_token
        self.channel_id = channel_id
        self.logger = logging.getLogger(__name__)
    
    def run(self):
        """Test connection in background"""
        try:
            client = TelegramClientSync(self.bot_token, self.channel_id)
            success, bot_username = client.test_connection()
            
            if success and bot_username:
                self.result_ready.emit(True, bot_username)
            else:
                self.result_ready.emit(False, "Connection failed")
                
        except Exception as e:
            self.logger.error(f"Telegram test error: {e}")
            self.result_ready.emit(False, str(e))


class AlertsTab(QWidget):
    """
    Tab containing alert configuration and monitoring functionality
    """

    config_changed = pyqtSignal()  # Emitted whenever any alert config changes

    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._current_user_list = []  # Track current users to detect changes
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize the alerts tab UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll area for entire content
        from PyQt6.QtWidgets import QScrollArea, QSplitter
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { background-color: #1a1f2e; }")
        
        # Container widget for scroll area
        container = QWidget()
        container.setStyleSheet("QWidget { background-color: #1a1f2e; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(10, 10, 10, 10)
        container_layout.setSpacing(0)
        
        # Telegram configuration section (fixed at top)
        self.telegram_config = TelegramConfigWidget()
        self.telegram_config.test_clicked.connect(self._on_test_telegram)
        self.telegram_config.config_changed.connect(self._on_config_changed)
        container_layout.addWidget(self.telegram_config)
        
        # Add separator line
        container_layout.addWidget(self._create_separator())
        container_layout.addSpacing(10)
        
        # Top row - horizontal splitter for Grid and MTM/ROI
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setStyleSheet("QSplitter { background-color: #1a1f2e; }")
        
        # Grid log alerts section
        self.grid_alerts = GridAlertsWidget()
        self.grid_alerts.config_changed.connect(self._on_config_changed)
        self.grid_alerts.setMinimumWidth(300)
        self.grid_alerts.setMinimumHeight(250)
        self.top_splitter.addWidget(self.grid_alerts)
        
        # MTM & ROI alerts section
        self.mtm_roi_alerts = MTMROIAlertsWidget()
        self.mtm_roi_alerts.config_changed.connect(self._on_config_changed)
        self.mtm_roi_alerts.setMinimumWidth(300)
        self.mtm_roi_alerts.setMinimumHeight(250)
        self.top_splitter.addWidget(self.mtm_roi_alerts)
        
        # Set initial sizes for top row
        self.top_splitter.setSizes([500, 500])
        self.top_splitter.splitterMoved.connect(self._on_splitter_moved)
        
        # Add top row to layout
        container_layout.addWidget(self.top_splitter)
        
        # Add resize handle for top row
        self.top_resize_handle = self._create_resize_handle('top')
        container_layout.addWidget(self.top_resize_handle)
        
        container_layout.addSpacing(10)
        
        # Bottom row - horizontal splitter for Margin and Quantity
        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter.setStyleSheet("QSplitter { background-color: #1a1f2e; }")
        
        # Margin alerts section
        self.margin_alerts = MarginAlertsWidget()
        self.margin_alerts.config_changed.connect(self._on_config_changed)
        self.margin_alerts.setMinimumWidth(300)
        self.margin_alerts.setMinimumHeight(250)
        self.bottom_splitter.addWidget(self.margin_alerts)
        
        # Quantity alerts section
        self.quantity_alerts = QuantityAlertsWidget()
        self.quantity_alerts.config_changed.connect(self._on_config_changed)
        self.quantity_alerts.setMinimumWidth(300)
        self.quantity_alerts.setMinimumHeight(250)
        self.bottom_splitter.addWidget(self.quantity_alerts)
        
        # Set initial sizes for bottom row
        self.bottom_splitter.setSizes([500, 500])
        self.bottom_splitter.splitterMoved.connect(self._on_splitter_moved)
        
        # Add bottom row to layout
        container_layout.addWidget(self.bottom_splitter)
        
        # Add resize handle for bottom row
        self.bottom_resize_handle = self._create_resize_handle('bottom')
        container_layout.addWidget(self.bottom_resize_handle)
        
        # Add stretch at the end to push everything up
        container_layout.addStretch()
        
        # Set container to scroll area
        scroll_area.setWidget(container)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Track dragging state
        self._dragging_handle = None
        self._drag_start_y = 0
        self._drag_start_height = 0
    
    def _create_resize_handle(self, handle_id):
        """Create a draggable resize handle"""
        from PyQt6.QtWidgets import QFrame
        handle = QFrame()
        handle.setObjectName(handle_id)
        handle.setFrameShape(QFrame.Shape.HLine)
        handle.setFixedHeight(8)
        handle.setCursor(Qt.CursorShape.SizeVerCursor)
        handle.setStyleSheet("""
            QFrame {
                background-color: #4a5568;
                margin: 0px 0px;
            }
            QFrame:hover {
                background-color: #4299e1;
            }
        """)
        
        # Install event filter for drag handling
        handle.mousePressEvent = lambda e: self._handle_press(handle_id, e)
        handle.mouseMoveEvent = lambda e: self._handle_move(handle_id, e)
        handle.mouseReleaseEvent = lambda e: self._handle_release(handle_id, e)
        
        return handle
    
    def _handle_press(self, handle_id, event):
        """Handle mouse press on resize handle"""
        self._dragging_handle = handle_id
        self._drag_start_y = event.globalPosition().y()
        
        if handle_id == 'top':
            self._drag_start_height = self.top_splitter.height()
        else:
            self._drag_start_height = self.bottom_splitter.height()
    
    def _handle_move(self, handle_id, event):
        """Handle mouse move while dragging"""
        if self._dragging_handle != handle_id:
            return
        
        # Calculate delta
        current_y = event.globalPosition().y()
        delta = current_y - self._drag_start_y
        new_height = max(250, self._drag_start_height + delta)
        
        # Apply new height
        if handle_id == 'top':
            self.top_splitter.setFixedHeight(int(new_height))
        else:
            self.bottom_splitter.setFixedHeight(int(new_height))
    
    def _handle_release(self, handle_id, event):
        """Handle mouse release"""
        if self._dragging_handle == handle_id:
            # Save final height
            if handle_id == 'top':
                height = self.top_splitter.height()
                self.settings_manager.settings.setValue('alerts/height/top', height)
            else:
                height = self.bottom_splitter.height()
                self.settings_manager.settings.setValue('alerts/height/bottom', height)
        
        self._dragging_handle = None
    
    def _create_separator(self):
        """Create a horizontal separator line"""
        from PyQt6.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("""
            QFrame {
                color: #4a5568;
                background-color: #4a5568;
                max-height: 1px;
                margin: 5px 0px;
            }
        """)
        return separator
    
    def _test_populate_users(self):
        """Temporary: Populate with test users"""
        # TODO: Remove this when connecting to real data
        test_users = ["USER1", "USER2", "USER3"]
        self.mtm_roi_alerts.update_users(test_users)
        self.margin_alerts.update_users(test_users)
        self.quantity_alerts.update_users(test_users)
    
    def verify_telegram_silent(self):
        """
        Silently verify Telegram credentials and update the indicator.
        Called automatically when engine starts. Does NOT send any message.
        """
        bot_token = self.telegram_config.get_bot_token()
        channel_id = self.telegram_config.get_channel_id()

        if not bot_token or not channel_id:
            self.telegram_config.set_connection_status(False)
            return

        self.verify_thread = TelegramVerifyThread(bot_token, channel_id)
        self.verify_thread.result_ready.connect(self._on_verify_result)
        self.verify_thread.start()

    def _on_verify_result(self, success, message):
        """Handle silent verification result"""
        if success:
            self.telegram_config.set_connection_status(True, message)
        else:
            self.telegram_config.set_connection_status(False)

    def _on_test_telegram(self):
        """Handle test telegram button click"""
        bot_token = self.telegram_config.get_bot_token()
        channel_id = self.telegram_config.get_channel_id()
        
        # Validate inputs
        if not bot_token or not channel_id:
            self.telegram_config.set_connection_status(False)
            return
        
        # Disable button during test
        self.telegram_config.test_button.setEnabled(False)
        self.telegram_config.test_button.setText("Testing...")
        
        # Run test in background thread
        self.test_thread = TelegramTestThread(bot_token, channel_id)
        self.test_thread.result_ready.connect(self._on_test_result)
        self.test_thread.start()
    
    def _on_test_result(self, success, message):
        """Handle test result from background thread"""
        # Re-enable button
        self.telegram_config.test_button.setEnabled(True)
        self.telegram_config.test_button.setText("Try TG trial alert")
        
        # Update status
        if success:
            self.telegram_config.set_connection_status(True, message)
        else:
            self.telegram_config.set_connection_status(False)
    
    def _on_config_changed(self):
        """Handle configuration changes - auto-save and notify main window"""
        self._save_settings()
        self.config_changed.emit()
    
    def _on_splitter_moved(self):
        """Handle splitter movement - save horizontal positions only"""
        self.settings_manager.settings.setValue('alerts/splitter/top', self.top_splitter.saveState())
        self.settings_manager.settings.setValue('alerts/splitter/bottom', self.bottom_splitter.saveState())
    
    def _save_splitter_positions(self):
        """Save splitter positions and row heights to settings"""
        # Horizontal positions
        self.settings_manager.settings.setValue('alerts/splitter/top', self.top_splitter.saveState())
        self.settings_manager.settings.setValue('alerts/splitter/bottom', self.bottom_splitter.saveState())
        
        # Row heights (if fixed)
        if hasattr(self.top_splitter, 'height'):
            top_height = self.top_splitter.height()
            if top_height > 250:  # Only save if manually resized
                self.settings_manager.settings.setValue('alerts/height/top', top_height)
        
        if hasattr(self.bottom_splitter, 'height'):
            bottom_height = self.bottom_splitter.height()
            if bottom_height > 250:
                self.settings_manager.settings.setValue('alerts/height/bottom', bottom_height)
    
    def _load_splitter_positions(self):
        """Load splitter positions and row heights from settings"""
        # Horizontal positions
        top_state = self.settings_manager.settings.value('alerts/splitter/top')
        bottom_state = self.settings_manager.settings.value('alerts/splitter/bottom')
        
        if top_state:
            self.top_splitter.restoreState(top_state)
        if bottom_state:
            self.bottom_splitter.restoreState(bottom_state)
        
        # Row heights
        top_height = self.settings_manager.settings.value('alerts/height/top', type=int)
        bottom_height = self.settings_manager.settings.value('alerts/height/bottom', type=int)
        
        if top_height and top_height > 250:
            self.top_splitter.setFixedHeight(top_height)
        
        if bottom_height and bottom_height > 250:
            self.bottom_splitter.setFixedHeight(bottom_height)
    
    def get_telegram_config(self):
        """Get reference to telegram config widget"""
        return self.telegram_config
    
    def get_grid_alerts(self):
        """Get reference to grid alerts widget"""
        return self.grid_alerts
    
    def get_mtm_roi_alerts(self):
        """Get reference to MTM/ROI alerts widget"""
        return self.mtm_roi_alerts
    
    def get_margin_alerts(self):
        """Get reference to margin alerts widget"""
        return self.margin_alerts
    
    def get_quantity_alerts(self):
        """Get reference to quantity alerts widget"""
        return self.quantity_alerts
    
    def set_aliases_hidden(self, hidden: bool):
        """
        Mask or restore user alias text in all alert tables.
        Replaces alias text with ***** rather than hiding the column,
        so the table layout stays intact.
        """
        for widget in (self.mtm_roi_alerts, self.margin_alerts, self.quantity_alerts):
            if not hasattr(widget, 'table'):
                continue
            tbl = widget.table
            for row in range(tbl.rowCount()):
                item = tbl.item(row, 0)
                if item is None:
                    continue
                if hidden:
                    # Store real alias if not already masked
                    if not item.data(32):   # Qt.ItemDataRole.UserRole = 32
                        item.setData(32, item.text())
                    item.setText('*****')
                else:
                    # Restore real alias from stored value
                    real = item.data(32)
                    if real:
                        item.setText(real)

    def update_users(self, user_aliases):
        """
        Update all alert tables with current user list
        Called when monitoring data updates
        
        Args:
            user_aliases: List of user alias strings
        """
        # Only update if user list has changed
        if sorted(user_aliases) == sorted(self._current_user_list):
            # User list unchanged, skip update to preserve scroll position
            return
        
        # User list changed, update tables
        self._current_user_list = user_aliases.copy()
        self.mtm_roi_alerts.update_users(user_aliases)
        self.margin_alerts.update_users(user_aliases)
        self.quantity_alerts.update_users(user_aliases)
        
        # Reload saved thresholds for these users
        self._reload_thresholds_for_users()
    
    def _reload_thresholds_for_users(self):
        """Reload saved thresholds after user list updates"""
        
        # MTM/ROI alerts
        enabled, thresholds = self.settings_manager.get_mtm_roi_config()
        
        for user_alias, user_thresholds in thresholds.items():
            if user_alias in self._current_user_list:
                self.mtm_roi_alerts.set_user_thresholds(user_alias, user_thresholds)

        # Margin alerts
        enabled, thresholds = self.settings_manager.get_margin_config()
        for user_alias, threshold in thresholds.items():
            if user_alias in self._current_user_list:
                self.margin_alerts.set_user_threshold(user_alias, threshold)

        # Quantity alerts
        enabled, thresholds = self.settings_manager.get_quantity_config()
        for user_alias, user_thresholds in thresholds.items():
            if user_alias in self._current_user_list:
                self.quantity_alerts.set_user_thresholds(user_alias, user_thresholds)

    def _load_settings(self):
        """Load all alert settings from SettingsManager"""
        # Block signals to prevent triggering saves during load
        self.telegram_config.blockSignals(True)
        self.grid_alerts.blockSignals(True)
        self.mtm_roi_alerts.blockSignals(True)
        self.margin_alerts.blockSignals(True)
        self.quantity_alerts.blockSignals(True)
        
        try:
            # Telegram config
            bot_token, channel_id, sound_enabled = self.settings_manager.get_telegram_config()
            self.telegram_config.set_bot_token(bot_token)
            self.telegram_config.set_channel_id(channel_id)
            self.telegram_config.set_sound_enabled(sound_enabled)
            
            # Grid log alerts
            (enabled, attention, error, warning, 
             filter_enabled, filter_keywords) = self.settings_manager.get_grid_alerts_config()
            self.grid_alerts.set_enabled(enabled)
            self.grid_alerts.set_attention_enabled(attention)
            self.grid_alerts.set_error_enabled(error)
            self.grid_alerts.set_warning_enabled(warning)
            self.grid_alerts.set_filter_enabled(filter_enabled)
            self.grid_alerts.set_filter_keywords(filter_keywords)
            
            # MTM/ROI alerts
            enabled, thresholds = self.settings_manager.get_mtm_roi_config()
            self.mtm_roi_alerts.set_enabled(enabled)
            # Don't load thresholds here - no users yet!
            # They will be loaded in _reload_thresholds_for_users()
            
            # Margin alerts
            enabled, thresholds = self.settings_manager.get_margin_config()
            self.margin_alerts.set_enabled(enabled)
            # Don't load thresholds here - no users yet!
            
            # Quantity alerts
            enabled, thresholds = self.settings_manager.get_quantity_config()
            self.quantity_alerts.set_enabled(enabled)
            # Don't load thresholds here - no users yet!
            
            # Load splitter positions
            self._load_splitter_positions()
        
        finally:
            # Re-enable signals
            self.telegram_config.blockSignals(False)
            self.grid_alerts.blockSignals(False)
            self.mtm_roi_alerts.blockSignals(False)
            self.margin_alerts.blockSignals(False)
            self.quantity_alerts.blockSignals(False)
    
    def _save_settings(self):
        """Save all alert settings to SettingsManager"""
        # Telegram config
        self.settings_manager.save_telegram_config(
            self.telegram_config.get_bot_token(),
            self.telegram_config.get_channel_id(),
            self.telegram_config.get_sound_enabled()
        )
        
        # Grid log alerts
        self.settings_manager.save_grid_alerts_config(
            self.grid_alerts.is_enabled(),
            self.grid_alerts.is_attention_enabled(),
            self.grid_alerts.is_error_enabled(),
            self.grid_alerts.is_warning_enabled(),
            self.grid_alerts.is_filter_enabled(),
            self.grid_alerts.get_filter_keywords()
        )
        
        # MTM/ROI alerts
        mtm_thresholds = self.mtm_roi_alerts.get_all_thresholds()
        self.settings_manager.save_mtm_roi_config(
            self.mtm_roi_alerts.is_enabled(),
            mtm_thresholds
        )
        
        # Margin alerts
        self.settings_manager.save_margin_config(
            self.margin_alerts.is_enabled(),
            self.margin_alerts.get_all_thresholds()
        )
        
        # Quantity alerts
        self.settings_manager.save_quantity_config(
            self.quantity_alerts.is_enabled(),
            self.quantity_alerts.get_all_thresholds()
        )
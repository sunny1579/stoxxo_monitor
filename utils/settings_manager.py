"""
Settings Manager
Handles saving and loading application settings
"""
from PyQt6.QtCore import QSettings
import logging
import json
import os


class SettingsManager:
    """
    Manages application settings persistence using QSettings
    Stores user preferences like column order, widths, window size, etc.
    """
    
    # Settings keys
    KEY_WINDOW_SIZE = "window/size"
    KEY_WINDOW_POSITION = "window/position"
    KEY_WINDOW_MAXIMIZED = "window/maximized"
    KEY_FONT_SIZE = "ui/font_size"
    KEY_POLLING_INTERVAL = "ui/polling_interval"
    KEY_PNL_HIDDEN = "ui/pnl_hidden"
    KEY_COLUMN_ORDER = "table/column_order"
    KEY_COLUMN_WIDTHS = "table/column_widths"
    KEY_SORT_COLUMN = "table/sort_column"
    KEY_SORT_ORDER = "table/sort_order"
    
    # Alert settings keys
    KEY_TELEGRAM_BOT_TOKEN = "alerts/telegram/bot_token"
    KEY_TELEGRAM_CHANNEL_ID = "alerts/telegram/channel_id"
    KEY_TELEGRAM_SOUND_ENABLED = "alerts/telegram/sound_enabled"
    
    KEY_GRID_ENABLED = "alerts/grid_log/enabled"
    KEY_GRID_ATTENTION = "alerts/grid_log/attention"
    KEY_GRID_ERROR = "alerts/grid_log/error"
    KEY_GRID_WARNING = "alerts/grid_log/warning"
    KEY_GRID_FILTER_ENABLED = "alerts/grid_log/filter_enabled"
    KEY_GRID_FILTER_KEYWORDS = "alerts/grid_log/filter_keywords"
    
    KEY_MTM_ROI_ENABLED = "alerts/mtm_roi/enabled"
    KEY_MARGIN_ENABLED = "alerts/margin/enabled"
    KEY_QUANTITY_ENABLED = "alerts/quantity/enabled"
    
    # JSON file for thresholds (QSettings doesn't handle nested dicts well)
    THRESHOLDS_FILE = "alert_thresholds.json"
    
    # Default values
    DEFAULT_FONT_SIZE = 11
    DEFAULT_POLLING_INTERVAL = 1.0
    DEFAULT_PNL_HIDDEN = False
    DEFAULT_WINDOW_WIDTH = 1400
    DEFAULT_WINDOW_HEIGHT = 800
    
    # Alert default values
    DEFAULT_TELEGRAM_SOUND = True
    DEFAULT_GRID_ENABLED = True
    DEFAULT_GRID_ATTENTION = True
    DEFAULT_GRID_ERROR = True
    DEFAULT_GRID_WARNING = True
    DEFAULT_GRID_FILTER_ENABLED = False
    DEFAULT_MTM_ROI_ENABLED = True
    DEFAULT_MARGIN_ENABLED = True
    DEFAULT_QUANTITY_ENABLED = True
    
    def __init__(self):
        """Initialize settings manager"""
        self.settings = QSettings("Stoxxo", "StoxxoMonitor")
        self.logger = logging.getLogger(__name__)
        
        # Get thresholds file path (same directory as exe/script)
        app_dir = os.path.dirname(os.path.abspath(__file__))
        self.thresholds_file_path = os.path.join(os.path.dirname(app_dir), self.THRESHOLDS_FILE)
        self.logger.debug(f"Thresholds file: {self.thresholds_file_path}")
        self.logger.info("Settings manager initialized")
    
    # Window Settings
    
    def save_window_geometry(self, window):
        """
        Save window size and position
        
        Args:
            window: QMainWindow instance
        """
        self.settings.setValue(self.KEY_WINDOW_SIZE, window.size())
        self.settings.setValue(self.KEY_WINDOW_POSITION, window.pos())
        self.settings.setValue(self.KEY_WINDOW_MAXIMIZED, window.isMaximized())
        self.logger.debug("Window geometry saved")
    
    def restore_window_geometry(self, window):
        """
        Restore window size and position
        
        Args:
            window: QMainWindow instance
        
        Returns:
            bool: True if restored, False if using defaults
        """
        size = self.settings.value(self.KEY_WINDOW_SIZE)
        position = self.settings.value(self.KEY_WINDOW_POSITION)
        maximized = self.settings.value(self.KEY_WINDOW_MAXIMIZED, False, type=bool)
        
        if size:
            window.resize(size)
            self.logger.debug(f"Window size restored: {size.width()}x{size.height()}")
        else:
            window.resize(self.DEFAULT_WINDOW_WIDTH, self.DEFAULT_WINDOW_HEIGHT)
            self.logger.debug("Using default window size")
        
        if position:
            window.move(position)
            self.logger.debug(f"Window position restored: {position.x()}, {position.y()}")
        
        if maximized:
            window.showMaximized()
            self.logger.debug("Window maximized")
        
        return size is not None
    
    # UI Settings
    
    def save_font_size(self, size):
        """Save table font size"""
        self.settings.setValue(self.KEY_FONT_SIZE, size)
        self.settings.sync()  # Force immediate write to disk
        self.logger.debug(f"Font size saved: {size}")
    
    def get_font_size(self):
        """Get saved font size"""
        size = self.settings.value(self.KEY_FONT_SIZE, self.DEFAULT_FONT_SIZE, type=int)
        self.logger.debug(f"Font size loaded: {size}")
        return size
    
    def save_polling_interval(self, interval):
        """Save polling interval"""
        self.settings.setValue(self.KEY_POLLING_INTERVAL, interval)
        self.logger.debug(f"Polling interval saved: {interval}")
    
    def get_polling_interval(self):
        """Get saved polling interval"""
        return self.settings.value(self.KEY_POLLING_INTERVAL, self.DEFAULT_POLLING_INTERVAL, type=float)
    
    def save_pnl_hidden(self, hidden):
        """Save P&L visibility state"""
        self.settings.setValue(self.KEY_PNL_HIDDEN, hidden)
        self.logger.debug(f"P&L hidden state saved: {hidden}")
    
    def get_pnl_hidden(self):
        """Get saved P&L visibility state"""
        return self.settings.value(self.KEY_PNL_HIDDEN, self.DEFAULT_PNL_HIDDEN, type=bool)
    
    # Table Settings
    
    def save_column_order(self, header):
        """
        Save current column order
        
        Args:
            header: QHeaderView instance
        """
        order = []
        for visual_index in range(header.count()):
            logical_index = header.logicalIndex(visual_index)
            order.append(logical_index)
        
        self.settings.setValue(self.KEY_COLUMN_ORDER, order)
        self.logger.debug(f"Column order saved: {order}")
    
    def restore_column_order(self, header):
        """
        Restore column order
        
        Args:
            header: QHeaderView instance
        
        Returns:
            bool: True if restored, False if using defaults
        """
        order = self.settings.value(self.KEY_COLUMN_ORDER)
        
        if order and len(order) == header.count():
            # Convert to integers (QSettings may return strings on Windows)
            try:
                order = [int(x) for x in order]
            except (ValueError, TypeError):
                self.logger.warning("Invalid column order data, using defaults")
                return False
            
            for visual_index, logical_index in enumerate(order):
                current_visual = header.visualIndex(logical_index)
                header.moveSection(current_visual, visual_index)
            
            self.logger.debug(f"Column order restored: {order}")
            return True
        
        self.logger.debug("Using default column order")
        return False
    
    def save_column_widths(self, header):
        """
        Save column widths
        
        Args:
            header: QHeaderView instance
        """
        widths = {}
        for i in range(header.count()):
            widths[i] = header.sectionSize(i)
        
        self.settings.setValue(self.KEY_COLUMN_WIDTHS, widths)
        self.logger.debug(f"Column widths saved: {widths}")
    
    def restore_column_widths(self, header):
        """
        Restore column widths
        
        Args:
            header: QHeaderView instance
        
        Returns:
            bool: True if restored, False if using defaults
        """
        widths = self.settings.value(self.KEY_COLUMN_WIDTHS)
        
        if widths:
            try:
                # Convert keys and values to integers (QSettings may return strings)
                for key, width in widths.items():
                    column_index = int(key)
                    column_width = int(width)
                    header.resizeSection(column_index, column_width)
                
                self.logger.debug(f"Column widths restored")
                return True
            except (ValueError, TypeError, AttributeError) as e:
                self.logger.warning(f"Invalid column width data: {e}, using defaults")
                return False
        
        self.logger.debug("Using default column widths")
        return False
    
    def save_sort_state(self, column, order):
        """
        Save table sort state
        
        Args:
            column: Column index
            order: Qt.SortOrder
        """
        self.settings.setValue(self.KEY_SORT_COLUMN, column)
        self.settings.setValue(self.KEY_SORT_ORDER, int(order))
        self.logger.debug(f"Sort state saved: column={column}, order={order}")
    
    def get_sort_state(self):
        """
        Get saved sort state
        
        Returns:
            tuple: (column, order) or (None, None) if not saved
        """
        column = self.settings.value(self.KEY_SORT_COLUMN)
        order = self.settings.value(self.KEY_SORT_ORDER)
        
        if column is not None and order is not None:
            return (int(column), int(order))
        
        return (None, None)
    
    # Alert Settings
    
    def save_telegram_config(self, bot_token, channel_id, sound_enabled):
        """Save Telegram configuration"""
        self.settings.setValue(self.KEY_TELEGRAM_BOT_TOKEN, bot_token)
        self.settings.setValue(self.KEY_TELEGRAM_CHANNEL_ID, channel_id)
        self.settings.setValue(self.KEY_TELEGRAM_SOUND_ENABLED, sound_enabled)
        self.logger.debug("Telegram config saved")
    
    def get_telegram_config(self):
        """Get Telegram configuration"""
        bot_token = self.settings.value(self.KEY_TELEGRAM_BOT_TOKEN, "")
        channel_id = self.settings.value(self.KEY_TELEGRAM_CHANNEL_ID, "")
        sound_enabled = self.settings.value(self.KEY_TELEGRAM_SOUND_ENABLED, 
                                           self.DEFAULT_TELEGRAM_SOUND, type=bool)
        return bot_token, channel_id, sound_enabled
    
    def save_grid_alerts_config(self, enabled, attention, error, warning, 
                                filter_enabled, filter_keywords):
        """Save grid log alerts configuration"""
        self.settings.setValue(self.KEY_GRID_ENABLED, enabled)
        self.settings.setValue(self.KEY_GRID_ATTENTION, attention)
        self.settings.setValue(self.KEY_GRID_ERROR, error)
        self.settings.setValue(self.KEY_GRID_WARNING, warning)
        self.settings.setValue(self.KEY_GRID_FILTER_ENABLED, filter_enabled)
        self.settings.setValue(self.KEY_GRID_FILTER_KEYWORDS, filter_keywords)
        self.logger.debug("Grid alerts config saved")
    
    def get_grid_alerts_config(self):
        """Get grid log alerts configuration"""
        enabled = self.settings.value(self.KEY_GRID_ENABLED, 
                                     self.DEFAULT_GRID_ENABLED, type=bool)
        attention = self.settings.value(self.KEY_GRID_ATTENTION, 
                                       self.DEFAULT_GRID_ATTENTION, type=bool)
        error = self.settings.value(self.KEY_GRID_ERROR, 
                                   self.DEFAULT_GRID_ERROR, type=bool)
        warning = self.settings.value(self.KEY_GRID_WARNING, 
                                     self.DEFAULT_GRID_WARNING, type=bool)
        filter_enabled = self.settings.value(self.KEY_GRID_FILTER_ENABLED, 
                                            self.DEFAULT_GRID_FILTER_ENABLED, type=bool)
        filter_keywords = self.settings.value(self.KEY_GRID_FILTER_KEYWORDS, [])
        
        # Ensure filter_keywords is a list
        if isinstance(filter_keywords, str):
            filter_keywords = [filter_keywords] if filter_keywords else []
        
        return enabled, attention, error, warning, filter_enabled, filter_keywords
    
    def save_mtm_roi_config(self, enabled, thresholds):
        """
        Save MTM/ROI alerts configuration
        
        Args:
            enabled: Boolean
            thresholds: Dict {user_alias: {mtm_above, mtm_below, roi_above, roi_below}}
        """
        self.settings.setValue(self.KEY_MTM_ROI_ENABLED, enabled)
        
        # Save thresholds to JSON file
        self._save_thresholds('mtm_roi', thresholds)
        self.logger.debug(f"MTM/ROI config saved for {len(thresholds)} users")
    
    def get_mtm_roi_config(self):
        """Get MTM/ROI alerts configuration"""
        enabled = self.settings.value(self.KEY_MTM_ROI_ENABLED, 
                                     self.DEFAULT_MTM_ROI_ENABLED, type=bool)
        
        # Load thresholds from JSON file
        thresholds = self._load_thresholds('mtm_roi')
        
        return enabled, thresholds
    
    def _save_thresholds(self, alert_type, thresholds):
        """
        Save thresholds to JSON file
        
        Args:
            alert_type: 'mtm_roi', 'margin', or 'quantity'
            thresholds: Dict of thresholds
        """
        try:
            
            # Load existing data
            all_thresholds = {}
            if os.path.exists(self.thresholds_file_path):
                with open(self.thresholds_file_path, 'r') as f:
                    all_thresholds = json.load(f)
            # else: file doesnt exist, all_thresholds stays empty dict
            
            # Update this alert type
            all_thresholds[alert_type] = thresholds
            
            # Save back to file
            with open(self.thresholds_file_path, 'w') as f:
                json.dump(all_thresholds, f, indent=2)
            
            self.logger.debug(f"Thresholds saved to {self.thresholds_file_path}")
        except Exception as e:
            self.logger.error(f"Error saving thresholds: {e}")
    
    def _load_thresholds(self, alert_type):
        """
        Load thresholds from JSON file
        
        Args:
            alert_type: 'mtm_roi', 'margin', or 'quantity'
            
        Returns:
            Dict of thresholds
        """
        try:
            
            if not os.path.exists(self.thresholds_file_path):
                return {}
            
            with open(self.thresholds_file_path, 'r') as f:
                all_thresholds = json.load(f)
            
            result = all_thresholds.get(alert_type, {})
            
            return result
        except Exception as e:
            self.logger.error(f"Error loading thresholds: {e}")
            return {}
    
    def save_margin_config(self, enabled, thresholds):
        """
        Save margin alerts configuration
        
        Args:
            enabled: Boolean
            thresholds: Dict {user_alias: margin_percent}
        """
        self.settings.setValue(self.KEY_MARGIN_ENABLED, enabled)
        self._save_thresholds('margin', thresholds)
        self.logger.debug(f"Margin config saved for {len(thresholds)} users")
    
    def get_margin_config(self):
        """Get margin alerts configuration"""
        enabled = self.settings.value(self.KEY_MARGIN_ENABLED, 
                                     self.DEFAULT_MARGIN_ENABLED, type=bool)
        thresholds = self._load_thresholds('margin')
        
        return enabled, thresholds
    
    def save_quantity_config(self, enabled, thresholds):
        """
        Save quantity alerts configuration
        
        Args:
            enabled: Boolean
            thresholds: Dict {user_alias: {calls_sell, puts_sell, calls_buy, 
                                          puts_buy, calls_net, puts_net}}
        """
        self.settings.setValue(self.KEY_QUANTITY_ENABLED, enabled)
        self._save_thresholds('quantity', thresholds)
        self.logger.debug(f"Quantity config saved for {len(thresholds)} users")
    
    def get_quantity_config(self):
        """Get quantity alerts configuration"""
        enabled = self.settings.value(self.KEY_QUANTITY_ENABLED, 
                                     self.DEFAULT_QUANTITY_ENABLED, type=bool)
        thresholds = self._load_thresholds('quantity')
        
        return enabled, thresholds
    
    # Reset to Defaults
    
    def reset_to_defaults(self):
        """Clear all settings and reset to defaults"""
        self.settings.clear()
        self.logger.info("All settings reset to defaults")
    
    def has_saved_settings(self):
        """Check if any settings are saved"""
        return len(self.settings.allKeys()) > 0
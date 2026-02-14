"""
Settings Manager
Handles saving and loading application settings
"""
from PyQt6.QtCore import QSettings
import logging


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
    
    # Default values
    DEFAULT_FONT_SIZE = 11
    DEFAULT_POLLING_INTERVAL = 1.0
    DEFAULT_PNL_HIDDEN = False
    DEFAULT_WINDOW_WIDTH = 1400
    DEFAULT_WINDOW_HEIGHT = 800
    
    def __init__(self):
        """Initialize settings manager"""
        self.settings = QSettings("Stoxxo", "StoxxoMonitor")
        self.logger = logging.getLogger(__name__)
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
        self.logger.info(f"Font size saved: {size} (saved to {self.settings.fileName()})")
    
    def get_font_size(self):
        """Get saved font size"""
        size = self.settings.value(self.KEY_FONT_SIZE, self.DEFAULT_FONT_SIZE, type=int)
        self.logger.info(f"Font size loaded: {size}")
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
    
    # Reset to Defaults
    
    def reset_to_defaults(self):
        """Clear all settings and reset to defaults"""
        self.settings.clear()
        self.logger.info("All settings reset to defaults")
    
    def has_saved_settings(self):
        """Check if any settings are saved"""
        return len(self.settings.allKeys()) > 0
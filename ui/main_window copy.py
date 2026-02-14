"""
Main Application Window
"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                              QLabel, QComboBox, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from datetime import datetime
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.widgets import MonitoringTable, EngineButton, MonitorStatusBar
from ui.polling_service import PollingService
from core.stoxxo_client import StoxxoClient
from utils.settings_manager import SettingsManager


class MainWindow(QMainWindow):
    """
    Main application window
    Combines all UI components
    """
    
    def __init__(self):
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        
        # Settings manager
        self.settings_manager = SettingsManager()
        
        # Stoxxo client
        self.client = None
        
        # Polling service
        self.poller = None
        
        # Current data storage (for P&L toggle)
        self._current_summaries = []
        
        # Current font size (will be loaded from settings)
        self.current_font_size = self.settings_manager.get_font_size()
        
        # Setup UI
        self._init_ui()
        
        # Load saved settings
        self._load_settings()
        
        # Initialize Stoxxo connection
        self._init_stoxxo()
    
    def _init_ui(self):
        """Initialize user interface"""
        self.setWindowTitle("Stoxxo User Quantity Monitoring Tool")
        self.setGeometry(100, 100, 1400, 800)
        # Remove minimum size restriction for full flexibility
        # self.setMinimumSize(1200, 600)  # Commented out
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Top bar
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Monitoring table
        self.table = MonitoringTable()
        main_layout.addWidget(self.table)
        
        # Status bar
        self.status_bar = MonitorStatusBar()
        self.setStatusBar(self.status_bar)
    
    def _create_top_bar(self):
        """Create top bar with ENGINE button and controls"""
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setMinimumHeight(80)
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # ENGINE button
        self.engine_btn = EngineButton()
        self.engine_btn.setMinimumSize(200, 60)
        self.engine_btn.engine_started.connect(self._on_engine_started)
        self.engine_btn.engine_stopped.connect(self._on_engine_stopped)
        layout.addWidget(self.engine_btn)
        
        # Spacer
        layout.addSpacing(30)
        
        # Title
        title_label = QLabel("Stoxxo User Quantity Monitoring Tool")
        title_label.setObjectName("headerLabel")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Spacer instead of stretch
        layout.addSpacing(50)
        
        # Font size controls
        font_label = QLabel("Font:")
        layout.addWidget(font_label)
        
        self.font_decrease_btn = QPushButton("-")
        self.font_decrease_btn.setFixedSize(35, 35)
        self.font_decrease_btn.clicked.connect(self._on_font_decrease)
        layout.addWidget(self.font_decrease_btn)
        
        self.font_size_label = QLabel(str(self.current_font_size))  # Use loaded value
        self.font_size_label.setFixedWidth(25)
        self.font_size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.font_size_label)
        
        self.font_increase_btn = QPushButton("+")
        self.font_increase_btn.setFixedSize(35, 35)
        self.font_increase_btn.clicked.connect(self._on_font_increase)
        layout.addWidget(self.font_increase_btn)
        
        layout.addSpacing(15)
        
        # P&L toggle button
        self.pnl_toggle_btn = QPushButton("Hide P&L")
        self.pnl_toggle_btn.setFixedSize(100, 35)
        self.pnl_toggle_btn.setCheckable(True)
        self.pnl_toggle_btn.setChecked(False)
        self.pnl_toggle_btn.clicked.connect(self._on_pnl_toggle)
        layout.addWidget(self.pnl_toggle_btn)
        
        layout.addSpacing(15)
        
        # Poll interval selector
        interval_label = QLabel("Poll:")
        layout.addWidget(interval_label)
        
        self.interval_combo = QComboBox()
        self.interval_combo.addItem("0.5s", 0.5)
        self.interval_combo.addItem("1s", 1.0)
        self.interval_combo.addItem("2s", 2.0)
        self.interval_combo.addItem("5s", 5.0)
        self.interval_combo.addItem("10s", 10.0)
        self.interval_combo.setCurrentIndex(1)
        self.interval_combo.currentIndexChanged.connect(self._on_interval_changed)
        layout.addWidget(self.interval_combo)
        
        layout.addSpacing(15)
        
        # Last update label
        self.last_update_label = QLabel("Last Update: Never")
        self.last_update_label.setObjectName("statusLabel")
        layout.addWidget(self.last_update_label)
        
        layout.addSpacing(15)
        
        # Reset to Defaults button
        self.reset_btn = QPushButton("Reset Defaults")
        self.reset_btn.setFixedSize(120, 35)
        self.reset_btn.clicked.connect(self._on_reset_defaults)
        layout.addWidget(self.reset_btn)
        
        # Push everything to the left
        layout.addStretch()
        
        return top_bar
    
    def _connect_settings_signals(self):
        """Connect signals to save settings immediately when changed"""
        # Save column order when moved
        header = self.table.horizontalHeader()
        header.sectionMoved.connect(self._on_column_moved)
        
        # Save column width when resized
        header.sectionResized.connect(self._on_column_resized)
        
        # Save sort state when sorted
        header.sortIndicatorChanged.connect(self._on_sort_changed)
    
    def _init_stoxxo(self):
        """Initialize Stoxxo client and polling service"""
        try:
            # Create client
            self.logger.info("Initializing Stoxxo client...")
            self.client = StoxxoClient()
            
            # Test connection (but don't block startup if failed)
            if self.client.status.ping():
                self.logger.info("Connected to Stoxxo Bridge")
                port = self.client.working_port or 21000
                self.status_bar.set_connection_status(True, port)
            else:
                self.logger.warning("Cannot connect to Stoxxo Bridge - will retry when ENGINE starts")
                self.status_bar.set_connection_status(False)
                # Don't show error dialog - just update status bar
            
            # Create polling service (even if not connected)
            self.poller = PollingService(self.client)
            self.poller.all_users_updated.connect(self._on_data_updated)
            self.poller.connection_status_changed.connect(self._on_connection_changed)
            self.poller.error_occurred.connect(self._on_error)
            
        except Exception as e:
            self.logger.error("Failed to initialize Stoxxo: %s", str(e))
            self.status_bar.set_connection_status(False)
            # Don't show error dialog on startup
    
    def _load_settings(self):
        """Load saved settings and apply them"""
        self.logger.info("Loading saved settings...")
        
        # Restore window geometry
        self.settings_manager.restore_window_geometry(self)
        
        # Restore font size (just load the value, apply later)
        saved_font_size = self.settings_manager.get_font_size()
        self.current_font_size = saved_font_size
        
        # Restore polling interval
        saved_interval = self.settings_manager.get_polling_interval()
        # Find matching index in combo box
        for i in range(self.interval_combo.count()):
            if abs(self.interval_combo.itemData(i) - saved_interval) < 0.01:
                self.interval_combo.setCurrentIndex(i)
                break
        
        # Restore P&L visibility state
        pnl_hidden = self.settings_manager.get_pnl_hidden()
        if pnl_hidden:
            self.pnl_toggle_btn.setChecked(True)
            self.pnl_toggle_btn.setText("Show P&L")
            self.table.pnl_hidden = True
        
        # Restore table settings
        header = self.table.horizontalHeader()
        
        # Restore column order
        self.settings_manager.restore_column_order(header)
        
        # Restore column widths
        self.settings_manager.restore_column_widths(header)
        
        # Restore sort state
        sort_column, sort_order = self.settings_manager.get_sort_state()
        if sort_column is not None:
            self.table.sortItems(sort_column, Qt.SortOrder(sort_order))
        
        # NOW apply the font after everything is set up
        # Use QTimer to ensure table is fully rendered before applying font
        QTimer.singleShot(100, self._update_table_font)
        
        # Connect signals to save settings immediately on changes
        self._connect_settings_signals()
        
        self.logger.info("Settings loaded successfully")
    
    def _on_engine_started(self):
        """Handle ENGINE START"""
        self.logger.info("Starting polling service...")
        
        # Check connection first
        if not self.client.status.ping():
            self.logger.warning("Cannot start - Stoxxo Bridge not connected")
            self._show_connection_error()
            self.engine_btn.stop()  # Revert button to START state
            return
        
        if self.poller:
            # Set interval
            interval = self.interval_combo.currentData()
            self.poller.set_interval(interval)
            
            # Start polling
            self.poller.start()
            
            # Update status bar
            self.status_bar.set_refresh_status(True, interval)
            
            self.logger.info("Polling service started")
        else:
            self.logger.error("Polling service not initialized")
            self.engine_btn.stop()
    
    def _on_engine_stopped(self):
        """Handle ENGINE STOP"""
        self.logger.info("Stopping polling service...")
        
        if self.poller and self.poller.isRunning():
            self.poller.stop()
            self.poller.wait()  # Wait for thread to finish
            
            # Update status bar
            self.status_bar.set_refresh_status(False)
            
            self.logger.info("Polling service stopped")
    
    def _on_data_updated(self, summaries):
        """
        Handle data update from polling service
        
        Args:
            summaries: List of OptionsPositionSummary objects
        """
        # Store summaries for P&L toggle
        self._current_summaries = summaries
        
        # Update table
        self.table.update_data(summaries)
        
        # Update status bar
        now = datetime.now()
        self.status_bar.set_last_update(now)
        self.last_update_label.setText("Last Update: %s" % now.strftime("%H:%M:%S"))
        
        self.logger.debug("Data updated: %d users", len(summaries))
    
    def _on_pnl_toggle(self):
        """Handle P&L visibility toggle"""
        is_hidden = self.pnl_toggle_btn.isChecked()
        
        if is_hidden:
            self.pnl_toggle_btn.setText("Show P&L")
            self.table.pnl_hidden = True
        else:
            self.pnl_toggle_btn.setText("Hide P&L")
            self.table.pnl_hidden = False
        
        # Refresh table with current data
        if hasattr(self, '_current_summaries'):
            self.table.update_data(self._current_summaries)
        
        # Save settings
        self.settings_manager.save_pnl_hidden(is_hidden)
    
    def _on_font_increase(self):
        """Increase table font size"""
        if self.current_font_size < 20:  # Max size 20
            self.current_font_size += 1
            self._update_table_font()
    
    def _on_font_decrease(self):
        """Decrease table font size"""
        if self.current_font_size > 8:  # Min size 8
            self.current_font_size -= 1
            self._update_table_font()
    
    def _update_table_font(self):
        """Update table font size"""
        # Update table font
        table_font = QFont()
        table_font.setPointSize(self.current_font_size)
        self.table.setFont(table_font)
        
        # Update header font
        header_font = QFont()
        header_font.setPointSize(self.current_font_size)
        header_font.setBold(True)
        self.table.horizontalHeader().setFont(header_font)
        
        # Update font size label
        self.font_size_label.setText(str(self.current_font_size))
        
        # Adjust row height based on font size
        row_height = int(self.current_font_size * 3.5)
        self.table.verticalHeader().setDefaultSectionSize(row_height)
        
        # Force update all existing items to use new font
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item_font = item.font()
                    item_font.setPointSize(self.current_font_size)
                    item.setFont(item_font)
        
        # Force table to repaint
        self.table.viewport().update()
        
        # Save settings
        self.settings_manager.save_font_size(self.current_font_size)
        
        self.logger.info("Font size changed to %d", self.current_font_size)
    
    def _on_connection_changed(self, is_connected):
        """
        Handle connection status change
        
        Args:
            is_connected: True if connected, False otherwise
        """
        if is_connected:
            port = self.client.working_port or 21000
            self.status_bar.set_connection_status(True, port)
            self.logger.info("Connection restored")
        else:
            self.status_bar.set_connection_status(False)
            self.logger.warning("Connection lost")
    
    def _on_error(self, error_msg):
        """
        Handle error from polling service
        
        Args:
            error_msg: Error message
        """
        self.logger.error("Polling error: %s", error_msg)
    
    def _on_interval_changed(self):
        """Handle poll interval change"""
        interval = self.interval_combo.currentData()
        
        if self.poller and self.poller.isRunning():
            # Update running poller
            self.poller.set_interval(interval)
            self.status_bar.set_refresh_status(True, interval)
            self.logger.info("Poll interval changed to %.1fs", interval)
        
        # Save settings
        self.settings_manager.save_polling_interval(interval)
    
    def _show_connection_error(self):
        """Show connection error dialog"""
        QMessageBox.warning(
            self,
            "Connection Error",
            "Cannot connect to Stoxxo Bridge.\n\n"
            "Please make sure:\n"
            "1. Stoxxo Bridge is running\n"
            "2. It's accessible at localhost:21000 or localhost:80\n\n"
            "You can update network settings if needed."
        )
    
    def _on_column_moved(self, logical_index, old_visual_index, new_visual_index):
        """Save settings when column is moved"""
        header = self.table.horizontalHeader()
        self.settings_manager.save_column_order(header)
        self.logger.debug(f"Column moved - settings saved")
    
    def _on_column_resized(self, logical_index, old_size, new_size):
        """Save settings when column is resized"""
        header = self.table.horizontalHeader()
        self.settings_manager.save_column_widths(header)
        self.logger.debug(f"Column resized - settings saved")
    
    def _on_sort_changed(self, logical_index, order):
        """Save settings when sort changes"""
        self.settings_manager.save_sort_state(logical_index, order)
        self.logger.debug(f"Sort changed - settings saved")
    
    def _on_reset_defaults(self):
        """Reset all settings to defaults"""
        # Confirm with user
        reply = QMessageBox.question(
            self,
            "Reset to Defaults",
            "Are you sure you want to reset all settings to defaults?\n\n"
            "This will reset:\n"
            "• Window size and position\n"
            "• Column order and widths\n"
            "• Font size\n"
            "• Polling interval\n"
            "• Sort preferences\n\n"
            "The application will restart after reset.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.info("Resetting all settings to defaults...")
            self.settings_manager.reset_to_defaults()
            
            # Show message and restart
            QMessageBox.information(
                self,
                "Reset Complete",
                "Settings have been reset to defaults.\n\n"
                "Please restart the application for changes to take effect."
            )
            
            # Close application
            self.close()
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.logger.info("Application closing - saving settings...")
        
        # Save all settings
        self._save_settings()
        
        # Stop polling if running
        if self.poller and self.poller.isRunning():
            self.logger.info("Stopping polling service...")
            self.poller.stop()
            self.poller.wait()
        
        self.logger.info("Application closed")
        event.accept()
    
    def _save_settings(self):
        """Save all current settings"""
        # Save window geometry
        self.settings_manager.save_window_geometry(self)
        
        # Save font size
        self.settings_manager.save_font_size(self.current_font_size)
        
        # Save polling interval
        current_interval = self.interval_combo.currentData()
        self.settings_manager.save_polling_interval(current_interval)
        
        # Save P&L visibility state
        self.settings_manager.save_pnl_hidden(self.pnl_toggle_btn.isChecked())
        
        # Save table settings
        header = self.table.horizontalHeader()
        
        # Save column order
        self.settings_manager.save_column_order(header)
        
        # Save column widths
        self.settings_manager.save_column_widths(header)
        
        # Save sort state
        sort_column = self.table.horizontalHeader().sortIndicatorSection()
        sort_order = self.table.horizontalHeader().sortIndicatorOrder()
        self.settings_manager.save_sort_state(sort_column, sort_order)
        
        self.logger.info("All settings saved")


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    from utils.logger import setup_logger
    
    # Setup logging
    logger = setup_logger()
    
    # Create application
    app = QApplication(sys.argv)
    
    # Load stylesheet
    try:
        stylesheet_path = os.path.join(
            os.path.dirname(__file__),
            'styles',
            'dark_theme.qss'
        )
        with open(stylesheet_path, 'r') as f:
            app.setStyleSheet(f.read())
            logger.info("Stylesheet loaded")
    except Exception as e:
        logger.error("Could not load stylesheet: %s", str(e))
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())
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


class MainWindow(QMainWindow):
    """
    Main application window
    Combines all UI components
    """
    
    def __init__(self):
        super().__init__()
        
        self.logger = logging.getLogger(__name__)
        
        # Stoxxo client
        self.client = None
        
        # Polling service
        self.poller = None
        
        # Current data storage (for P&L toggle)
        self._current_summaries = []
        
        # Current font size
        self.current_font_size = 11
        
        # Setup UI
        self._init_ui()
        
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
        
        self.font_size_label = QLabel("11")
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
        
        # Push everything to the left
        layout.addStretch()
        
        return top_bar
    
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
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop polling if running
        if self.poller and self.poller.isRunning():
            self.logger.info("Stopping polling service before exit...")
            self.poller.stop()
            self.poller.wait()
        
        self.logger.info("Application closing")
        event.accept()


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
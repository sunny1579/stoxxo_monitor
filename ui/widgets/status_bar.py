"""
Status Bar Widget
Displays connection status, last update time, and other info
"""
from PyQt6.QtWidgets import QStatusBar, QLabel
from PyQt6.QtCore import Qt
from datetime import datetime


class MonitorStatusBar(QStatusBar):
    """
    Custom status bar for monitoring application
    Shows: Connection status | Last update | Version
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create status labels
        self._create_labels()
        
        # Initial state
        self.set_connection_status(False)
        self.set_last_update(None)
    
    def _create_labels(self):
        """Create and add status labels"""
        # Connection status
        self.connection_label = QLabel("Bridge: Disconnected")
        self.connection_label.setObjectName("connectionStatus")
        self.connection_label.setProperty("connected", "false")
        self.addWidget(self.connection_label)
        
        # Separator
        self.addWidget(self._create_separator())
        
        # Last update time
        self.update_label = QLabel("Last Update: Never")
        self.addWidget(self.update_label)
        
        # Separator
        self.addWidget(self._create_separator())
        
        # Auto-refresh status
        self.refresh_label = QLabel("Auto-refresh: OFF")
        self.addWidget(self.refresh_label)
        
        # Stretch to push version to right
        self.addPermanentWidget(QLabel(""))  # Spacer
        
        # Version (right side)
        self.version_label = QLabel("v1.0.0")
        self.version_label.setObjectName("statusLabel")
        self.addPermanentWidget(self.version_label)
    
    def _create_separator(self):
        """Create vertical separator"""
        sep = QLabel("|")
        sep.setObjectName("statusLabel")
        return sep
    
    def set_connection_status(self, connected, port=None):
        """
        Update connection status
        
        Args:
            connected: True if connected, False otherwise
            port: Bridge port number (optional)
        """
        if connected:
            if port:
                text = "Bridge: Connected (localhost:%d)" % port
            else:
                text = "Bridge: Connected"
            self.connection_label.setProperty("connected", "true")
        else:
            text = "Bridge: Disconnected"
            self.connection_label.setProperty("connected", "false")
        
        self.connection_label.setText(text)
        
        # Force style refresh
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)
        self.connection_label.update()
    
    def set_last_update(self, timestamp=None):
        """
        Update last update time
        
        Args:
            timestamp: datetime object or None
        """
        if timestamp:
            time_str = timestamp.strftime("%H:%M:%S")
            self.update_label.setText("Last Update: %s" % time_str)
        else:
            self.update_label.setText("Last Update: Never")
    
    def set_refresh_status(self, enabled, interval=None):
        """
        Update auto-refresh status
        
        Args:
            enabled: True if auto-refresh is on
            interval: Refresh interval in seconds (optional)
        """
        if enabled:
            if interval:
                self.refresh_label.setText("Auto-refresh: ON (%.1fs)" % interval)
            else:
                self.refresh_label.setText("Auto-refresh: ON")
        else:
            self.refresh_label.setText("Auto-refresh: OFF")
    
    def set_user_count(self, count):
        """
        Update user count display
        
        Args:
            count: Number of users
        """
        # Can add this to show user count if needed
        pass


if __name__ == "__main__":
    # Test the status bar
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    
    app = QApplication(sys.argv)
    
    # Load stylesheet
    try:
        with open('../styles/dark_theme.qss', 'r') as f:
            app.setStyleSheet(f.read())
    except:
        print("Could not load stylesheet")
    
    # Create window
    window = QMainWindow()
    window.setWindowTitle("Status Bar Test")
    window.setGeometry(100, 100, 800, 200)
    
    # Status bar
    status_bar = MonitorStatusBar()
    window.setStatusBar(status_bar)
    
    # Central widget with test buttons
    central = QWidget()
    layout = QVBoxLayout(central)
    
    # Test buttons
    def test_connected():
        status_bar.set_connection_status(True, 21000)
        status_bar.set_last_update(datetime.now())
        status_bar.set_refresh_status(True, 1.0)
    
    def test_disconnected():
        status_bar.set_connection_status(False)
        status_bar.set_refresh_status(False)
    
    btn_connected = QPushButton("Simulate Connected")
    btn_connected.clicked.connect(test_connected)
    layout.addWidget(btn_connected)
    
    btn_disconnected = QPushButton("Simulate Disconnected")
    btn_disconnected.clicked.connect(test_disconnected)
    layout.addWidget(btn_disconnected)
    
    window.setCentralWidget(central)
    window.show()
    
    sys.exit(app.exec())
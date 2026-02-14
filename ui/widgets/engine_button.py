"""
ENGINE Button Widget
Toggleable start/stop button for polling service
"""
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import pyqtSignal, Qt


class EngineButton(QPushButton):
    """
    ENGINE START/STOP button
    Changes appearance and text based on state
    """
    
    # Signals
    engine_started = pyqtSignal()
    engine_stopped = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.is_running = False
        
        # Setup
        self.setObjectName("engineButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_appearance()
        
        # Connect click
        self.clicked.connect(self._on_clicked)
    
    def _update_appearance(self):
        """Update button text and properties based on state"""
        if self.is_running:
            self.setText("ENGINE STOP")
            self.setProperty("running", "true")
        else:
            self.setText("ENGINE START")
            self.setProperty("running", "false")
        
        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
    
    def _on_clicked(self):
        """Handle button click"""
        if self.is_running:
            self.stop()
        else:
            self.start()
    
    def start(self):
        """Start the engine (switch to STOP state)"""
        if not self.is_running:
            self.is_running = True
            self._update_appearance()
            self.engine_started.emit()
    
    def stop(self):
        """Stop the engine (switch to START state)"""
        if self.is_running:
            self.is_running = False
            self._update_appearance()
            self.engine_stopped.emit()
    
    def set_running(self, running):
        """
        Programmatically set running state
        
        Args:
            running: True for running, False for stopped
        """
        if running:
            self.start()
        else:
            self.stop()


if __name__ == "__main__":
    # Test the button
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
    
    app = QApplication(sys.argv)
    
    # Load stylesheet
    try:
        with open('../styles/dark_theme.qss', 'r') as f:
            app.setStyleSheet(f.read())
    except:
        print("Could not load stylesheet")
    
    # Create window
    window = QMainWindow()
    window.setWindowTitle("ENGINE Button Test")
    window.setGeometry(100, 100, 400, 300)
    
    # Central widget
    central = QWidget()
    layout = QVBoxLayout(central)
    
    # Status label
    status_label = QLabel("Status: Stopped")
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(status_label)
    
    # ENGINE button
    engine_btn = EngineButton()
    layout.addWidget(engine_btn)
    
    # Connect signals
    def on_started():
        status_label.setText("Status: RUNNING")
        print("Engine started!")
    
    def on_stopped():
        status_label.setText("Status: STOPPED")
        print("Engine stopped!")
    
    engine_btn.engine_started.connect(on_started)
    engine_btn.engine_stopped.connect(on_stopped)
    
    window.setCentralWidget(central)
    window.show()
    
    sys.exit(app.exec())
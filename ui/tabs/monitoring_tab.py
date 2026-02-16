"""
Monitoring Tab
Contains the position monitoring table and controls
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from ui.widgets import MonitoringTable


class MonitoringTab(QWidget):
    """
    Tab containing the position monitoring functionality
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the monitoring tab UI"""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Monitoring table
        self.table = MonitoringTable()
        layout.addWidget(self.table)
    
    def get_table(self):
        """Get reference to the monitoring table"""
        return self.table
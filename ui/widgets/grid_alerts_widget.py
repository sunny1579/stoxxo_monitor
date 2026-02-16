"""
Grid Log Alerts Widget
Section for configuring grid log error alerts
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QCheckBox, QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal


class GridAlertsWidget(QGroupBox):
    """
    Widget for configuring grid log alert settings
    """
    
    # Signal
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("")  # No title, we'll add our own styled header
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable TG alerts for grid log errors")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setStyleSheet(self._get_checkbox_style())
        self.enable_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.enable_checkbox)
        
        main_layout.addSpacing(8)
        
        # Alert type checkboxes
        self.attention_checkbox = QCheckBox("ATTENTION")
        self.attention_checkbox.setChecked(True)
        self.attention_checkbox.setStyleSheet(self._get_checkbox_style())
        self.attention_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.attention_checkbox)
        
        self.error_checkbox = QCheckBox("ERROR")
        self.error_checkbox.setChecked(True)
        self.error_checkbox.setStyleSheet(self._get_checkbox_style())
        self.error_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.error_checkbox)
        
        self.warning_checkbox = QCheckBox("WARNING")
        self.warning_checkbox.setChecked(True)
        self.warning_checkbox.setStyleSheet(self._get_checkbox_style())
        self.warning_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.warning_checkbox)
        
        main_layout.addSpacing(12)
        
        # Filter section
        self.filter_checkbox = QCheckBox("Skips such error alerts which contain below\nstring in grid log error line")
        self.filter_checkbox.setChecked(False)
        self.filter_checkbox.setStyleSheet(self._get_checkbox_style())
        self.filter_checkbox.stateChanged.connect(self._on_filter_checkbox_changed)
        main_layout.addWidget(self.filter_checkbox)
        
        main_layout.addSpacing(5)
        
        # Filter input
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Enter keywords separated by commas (e.g., ConnectionTimeout, NetworkError)")
        self.filter_input.setEnabled(False)  # Disabled by default
        self.filter_input.textChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.filter_input)
        
        # Set group box styling
        self.setStyleSheet("""
            QGroupBox {
                background-color: #2d3748;
                border: 1px solid #4a5568;
                border-radius: 6px;
                margin-top: 0px;
                padding-top: 10px;
            }
        """)
    
    def _get_checkbox_style(self):
        """Get checkbox stylesheet"""
        return """
            QCheckBox {
                color: #ffffff;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #4a5568;
                border-radius: 3px;
                background-color: #1a1f2e;
            }
            QCheckBox::indicator:checked {
                background-color: #4299e1;
                border-color: #4299e1;
                image: url(none);
            }
            QCheckBox::indicator:hover {
                border-color: #718096;
            }
            QCheckBox::indicator:disabled {
                background-color: #2d3748;
                border-color: #4a5568;
            }
        """
    
    def _on_filter_checkbox_changed(self):
        """Handle filter checkbox state change"""
        self.filter_input.setEnabled(self.filter_checkbox.isChecked())
        self._on_config_changed()
    
    def _on_config_changed(self):
        """Emit config changed signal"""
        self.config_changed.emit()
    
    # Getters
    def is_enabled(self):
        """Check if grid log alerts are enabled"""
        return self.enable_checkbox.isChecked()
    
    def is_attention_enabled(self):
        """Check if ATTENTION alerts are enabled"""
        return self.attention_checkbox.isChecked()
    
    def is_error_enabled(self):
        """Check if ERROR alerts are enabled"""
        return self.error_checkbox.isChecked()
    
    def is_warning_enabled(self):
        """Check if WARNING alerts are enabled"""
        return self.warning_checkbox.isChecked()
    
    def is_filter_enabled(self):
        """Check if filter is enabled"""
        return self.filter_checkbox.isChecked()
    
    def get_filter_keywords(self):
        """Get filter keywords as list"""
        text = self.filter_input.text().strip()
        if not text:
            return []
        # Split by comma and strip whitespace
        return [kw.strip() for kw in text.split(',') if kw.strip()]
    
    # Setters
    def set_enabled(self, enabled):
        """Set enabled state"""
        self.enable_checkbox.setChecked(enabled)
    
    def set_attention_enabled(self, enabled):
        """Set ATTENTION enabled state"""
        self.attention_checkbox.setChecked(enabled)
    
    def set_error_enabled(self, enabled):
        """Set ERROR enabled state"""
        self.error_checkbox.setChecked(enabled)
    
    def set_warning_enabled(self, enabled):
        """Set WARNING enabled state"""
        self.warning_checkbox.setChecked(enabled)
    
    def set_filter_enabled(self, enabled):
        """Set filter enabled state"""
        self.filter_checkbox.setChecked(enabled)
    
    def set_filter_keywords(self, keywords):
        """Set filter keywords from list"""
        if isinstance(keywords, list):
            self.filter_input.setText(', '.join(keywords))
        else:
            self.filter_input.setText(keywords)
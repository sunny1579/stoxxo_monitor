"""
Telegram Configuration Widget
Top section of Alerts tab for Telegram bot configuration
"""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QCheckBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


class TelegramConfigWidget(QWidget):
    """
    Widget for configuring Telegram bot settings
    """
    
    # Signals
    test_clicked = pyqtSignal()  # When test button is clicked
    config_changed = pyqtSignal()  # When any config value changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        
        # First row: Bot ID, Channel ID, Test button
        first_row = QHBoxLayout()
        first_row.setSpacing(15)
        
        # Bot ID
        bot_label = QLabel("TG bot id:")
        bot_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        first_row.addWidget(bot_label)
        
        self.bot_id_input = QLineEdit()
        self.bot_id_input.setPlaceholderText("Enter bot token")
        self.bot_id_input.setFixedWidth(300)
        self.bot_id_input.setEchoMode(QLineEdit.EchoMode.Password)  # Hide token
        self.bot_id_input.textChanged.connect(self._on_config_changed)
        first_row.addWidget(self.bot_id_input)
        
        first_row.addSpacing(20)
        
        # Channel ID
        channel_label = QLabel("TG channel id:")
        channel_label.setStyleSheet("color: #ffffff; font-size: 12px;")
        first_row.addWidget(channel_label)
        
        self.channel_id_input = QLineEdit()
        self.channel_id_input.setPlaceholderText("-1003220645575")
        self.channel_id_input.setFixedWidth(200)
        self.channel_id_input.textChanged.connect(self._on_config_changed)
        first_row.addWidget(self.channel_id_input)
        
        first_row.addSpacing(20)
        
        # Test button
        self.test_button = QPushButton("Try TG trial alert")
        self.test_button.setFixedWidth(150)
        self.test_button.clicked.connect(self.test_clicked.emit)
        self.test_button.setStyleSheet("""
            QPushButton {
                background-color: #4299e1;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
            QPushButton:pressed {
                background-color: #2c5282;
            }
            QPushButton:disabled {
                background-color: #4a5568;
                color: #a0aec0;
            }
        """)
        first_row.addWidget(self.test_button)
        
        first_row.addStretch()
        
        main_layout.addLayout(first_row)
        
        # Second row: Connection status and sound checkbox
        second_row = QHBoxLayout()
        second_row.setSpacing(30)
        
        # Connection status
        status_container = QHBoxLayout()
        status_container.setSpacing(8)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("""
            color: #f56565;
            font-size: 16px;
        """)
        status_container.addWidget(self.status_indicator)
        
        self.status_text = QLabel("TG connection status")
        self.status_text.setStyleSheet("color: #a0aec0; font-size: 11px;")
        status_container.addWidget(self.status_text)
        
        second_row.addLayout(status_container)
        
        second_row.addSpacing(50)
        
        # Sound checkbox
        self.sound_checkbox = QCheckBox("Enable sound on any TG alert")
        self.sound_checkbox.setChecked(True)
        self.sound_checkbox.setStyleSheet("""
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
                background-color: #2d3748;
            }
            QCheckBox::indicator:checked {
                background-color: #4299e1;
                border-color: #4299e1;
                image: url(none);
            }
            QCheckBox::indicator:hover {
                border-color: #718096;
            }
        """)
        self.sound_checkbox.stateChanged.connect(self._on_config_changed)
        second_row.addWidget(self.sound_checkbox)
        
        second_row.addStretch()
        
        main_layout.addLayout(second_row)
    
    def _on_config_changed(self):
        """Emit config changed signal"""
        self.config_changed.emit()
    
    def set_connection_status(self, connected, bot_username=None):
        """
        Update connection status display
        
        Args:
            connected: True if connected, False otherwise
            bot_username: Bot username (optional)
        """
        if connected:
            self.status_indicator.setStyleSheet("color: #48bb78; font-size: 16px;")
            if bot_username:
                self.status_text.setText(f"TG connection status - Connected (@{bot_username})")
            else:
                self.status_text.setText("TG connection status - Connected")
            self.status_text.setStyleSheet("color: #48bb78; font-size: 11px; font-weight: bold;")
        else:
            self.status_indicator.setStyleSheet("color: #f56565; font-size: 16px;")
            self.status_text.setText("TG connection status - Disconnected")
            self.status_text.setStyleSheet("color: #f56565; font-size: 11px;")
    
    def get_bot_token(self):
        """Get bot token"""
        return self.bot_id_input.text().strip()
    
    def get_channel_id(self):
        """Get channel ID"""
        return self.channel_id_input.text().strip()
    
    def get_sound_enabled(self):
        """Get sound enabled state"""
        return self.sound_checkbox.isChecked()
    
    def set_bot_token(self, token):
        """Set bot token"""
        self.bot_id_input.setText(token)
    
    def set_channel_id(self, channel_id):
        """Set channel ID"""
        self.channel_id_input.setText(channel_id)
    
    def set_sound_enabled(self, enabled):
        """Set sound enabled state"""
        self.sound_checkbox.setChecked(enabled)
    
    def set_enabled(self, enabled):
        """Enable/disable all controls"""
        self.bot_id_input.setEnabled(enabled)
        self.channel_id_input.setEnabled(enabled)
        self.test_button.setEnabled(enabled)
        self.sound_checkbox.setEnabled(enabled)
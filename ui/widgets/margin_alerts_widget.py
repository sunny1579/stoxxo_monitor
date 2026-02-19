"""
Margin Alerts Widget
Section for configuring Utilised Margin % threshold alerts per user
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QCheckBox, QTableWidget, 
                              QTableWidgetItem, QGroupBox, QHeaderView, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator


class MarginAlertsWidget(QGroupBox):
    """
    Widget for configuring Utilised Margin % alert thresholds per user
    """
    
    # Signal
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("")
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable TG alerts for Utilised margin %")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setStyleSheet(self._get_checkbox_style())
        self.enable_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.enable_checkbox)
        
        main_layout.addSpacing(8)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([
            "user\nalias",
            "UT Margin\n% above"
        ])
        
        # Table properties
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(150)
        # Removed setMaximumHeight to allow table to expand with container
        
        # Column resize modes - all interactive (resizable by width only)
        header = self.table.horizontalHeader()
        for col in range(2):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 150)  # user alias
        self.table.setColumnWidth(1, 150)  # UT Margin % above
        
        # Prevent column reordering
        header.setSectionsMovable(False)
        
        main_layout.addWidget(self.table)
        
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
        """
    
    def _create_editable_cell(self, value=""):
        """
        Create an editable cell with a QLineEdit
        
        Args:
            value: Initial value
            
        Returns:
            QLineEdit widget
        """
        line_edit = QLineEdit()
        line_edit.setText(str(value) if value else "")
        line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Validator for numeric input (0-100 for percentage)
        validator = QDoubleValidator(0.0, 100.0, 2)
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        line_edit.setValidator(validator)
        
        # Style
        line_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1a1f2e;
                color: #e2e8f0;
                border: 1px solid #4a5568;
                border-radius: 3px;
                padding: 4px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #4299e1;
            }
        """)
        
        # Connect to config changed
        line_edit.textChanged.connect(self._on_config_changed)
        
        return line_edit
    
    def _on_config_changed(self):
        """Emit config changed signal"""
        self.config_changed.emit()
    
    def update_users(self, user_aliases):
        """
        Update table with list of user aliases
        Auto-creates rows for new users, preserves existing thresholds
        
        Args:
            user_aliases: List of user alias strings
        """
        # Get current values before clearing
        current_values = self.get_all_thresholds()
        
        # Clear table
        self.table.setRowCount(0)
        
        # Add rows for each user
        for user_alias in user_aliases:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # User alias (non-editable)
            alias_item = QTableWidgetItem(user_alias)
            alias_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            alias_item.setFlags(alias_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            alias_item.setData(32, user_alias)  # store real alias in UserRole
            self.table.setItem(row, 0, alias_item)
            
            # Get saved value for this user if exists
            saved_value = current_values.get(user_alias, '')
            
            # Margin % above
            margin_input = self._create_editable_cell(saved_value)
            self.table.setCellWidget(row, 1, margin_input)
        
        # Adjust row heights
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 35)
    
    def get_all_thresholds(self):
        """
        Get all threshold values for all users
        
        Returns:
            Dict: {user_alias: margin_percent_above}
        """
        thresholds = {}
        
        for row in range(self.table.rowCount()):
            # Get user alias
            alias_item = self.table.item(row, 0)
            if not alias_item:
                continue
            # Read from UserRole so it works even when text is masked as *****
            user_alias = alias_item.data(32) or alias_item.text()
            
            # Get threshold value
            margin_widget = self.table.cellWidget(row, 1)
            thresholds[user_alias] = margin_widget.text() if margin_widget else ''
        
        return thresholds
    
    def set_user_threshold(self, user_alias, threshold):
        """
        Set threshold for a specific user
        
        Args:
            user_alias: User alias string
            threshold: Margin percentage threshold value
        """
        # Find row for this user
        for row in range(self.table.rowCount()):
            alias_item = self.table.item(row, 0)
            if alias_item and alias_item.text() == user_alias:
                # Set value
                margin_input = self.table.cellWidget(row, 1)
                if margin_input:
                    margin_input.blockSignals(True)  # Block signal during set
                    margin_input.setText(str(threshold))
                    margin_input.blockSignals(False)
                break
    
    def is_enabled(self):
        """Check if margin alerts are enabled"""
        return self.enable_checkbox.isChecked()
    
    def set_enabled(self, enabled):
        """Set enabled state"""
        self.enable_checkbox.setChecked(enabled)
"""
Quantity Alerts Widget
Section for configuring live position quantity threshold alerts per user
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QCheckBox, QTableWidget, 
                              QTableWidgetItem, QGroupBox, QHeaderView, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator


class QuantityAlertsWidget(QGroupBox):
    """
    Widget for configuring position quantity alert thresholds per user
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
        self.enable_checkbox = QCheckBox("Enable TG alerts for live positions quantity exceeds")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setStyleSheet(self._get_checkbox_style())
        self.enable_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.enable_checkbox)
        
        main_layout.addSpacing(8)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "user\nalias",
            "calls sell\nquantity\nabove",
            "puts sell\nquantity\nabove",
            "calls buy\nquantity\nabove",
            "puts buy\nquantity\nabove",
            "calls net\nquantity\nabove",
            "puts net\nquantity\nabove"
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
        for col in range(7):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 100)  # user alias
        self.table.setColumnWidth(1, 90)   # calls sell
        self.table.setColumnWidth(2, 90)   # puts sell
        self.table.setColumnWidth(3, 90)   # calls buy
        self.table.setColumnWidth(4, 90)   # puts buy
        self.table.setColumnWidth(5, 90)   # calls net
        self.table.setColumnWidth(6, 90)   # puts net
        
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
        
        # Validator for positive integer input only (quantities must be positive)
        validator = QIntValidator(0, 999999)
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
            
            # Get saved values for this user if they exist
            saved = current_values.get(user_alias, {})
            
            # Calls sell quantity above
            calls_sell_input = self._create_editable_cell(saved.get('calls_sell', ''))
            self.table.setCellWidget(row, 1, calls_sell_input)
            
            # Puts sell quantity above
            puts_sell_input = self._create_editable_cell(saved.get('puts_sell', ''))
            self.table.setCellWidget(row, 2, puts_sell_input)
            
            # Calls buy quantity above
            calls_buy_input = self._create_editable_cell(saved.get('calls_buy', ''))
            self.table.setCellWidget(row, 3, calls_buy_input)
            
            # Puts buy quantity above
            puts_buy_input = self._create_editable_cell(saved.get('puts_buy', ''))
            self.table.setCellWidget(row, 4, puts_buy_input)
            
            # Calls net quantity above
            calls_net_input = self._create_editable_cell(saved.get('calls_net', ''))
            self.table.setCellWidget(row, 5, calls_net_input)
            
            # Puts net quantity above
            puts_net_input = self._create_editable_cell(saved.get('puts_net', ''))
            self.table.setCellWidget(row, 6, puts_net_input)
        
        # Adjust row heights
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 35)
    
    def get_all_thresholds(self):
        """
        Get all threshold values for all users
        
        Returns:
            Dict: {user_alias: {calls_sell, puts_sell, calls_buy, puts_buy, calls_net, puts_net}}
        """
        thresholds = {}
        
        for row in range(self.table.rowCount()):
            # Get user alias
            alias_item = self.table.item(row, 0)
            if not alias_item:
                continue
            # Read from UserRole so it works even when text is masked as *****
            user_alias = alias_item.data(32) or alias_item.text()
            
            # Get threshold values
            calls_sell = self.table.cellWidget(row, 1)
            puts_sell = self.table.cellWidget(row, 2)
            calls_buy = self.table.cellWidget(row, 3)
            puts_buy = self.table.cellWidget(row, 4)
            calls_net = self.table.cellWidget(row, 5)
            puts_net = self.table.cellWidget(row, 6)
            
            thresholds[user_alias] = {
                'calls_sell': calls_sell.text() if calls_sell else '',
                'puts_sell': puts_sell.text() if puts_sell else '',
                'calls_buy': calls_buy.text() if calls_buy else '',
                'puts_buy': puts_buy.text() if puts_buy else '',
                'calls_net': calls_net.text() if calls_net else '',
                'puts_net': puts_net.text() if puts_net else ''
            }
        
        return thresholds
    
    def set_user_thresholds(self, user_alias, thresholds):
        """
        Set thresholds for a specific user
        
        Args:
            user_alias: User alias string
            thresholds: Dict with keys: calls_sell, puts_sell, calls_buy, puts_buy, calls_net, puts_net
        """
        # Find row for this user
        for row in range(self.table.rowCount()):
            alias_item = self.table.item(row, 0)
            if alias_item and alias_item.text() == user_alias:
                # Set values
                widgets = [
                    self.table.cellWidget(row, 1),  # calls_sell
                    self.table.cellWidget(row, 2),  # puts_sell
                    self.table.cellWidget(row, 3),  # calls_buy
                    self.table.cellWidget(row, 4),  # puts_buy
                    self.table.cellWidget(row, 5),  # calls_net
                    self.table.cellWidget(row, 6),  # puts_net
                ]
                keys = ['calls_sell', 'puts_sell', 'calls_buy', 'puts_buy', 'calls_net', 'puts_net']
                
                # Block signals on all widgets
                for widget in widgets:
                    if widget:
                        widget.blockSignals(True)
                
                # Set values
                for widget, key in zip(widgets, keys):
                    if widget:
                        widget.setText(str(thresholds.get(key, '')))
                
                # Unblock signals
                for widget in widgets:
                    if widget:
                        widget.blockSignals(False)
                
                break
    
    def is_enabled(self):
        """Check if quantity alerts are enabled"""
        return self.enable_checkbox.isChecked()
    
    def set_enabled(self, enabled):
        """Set enabled state"""
        self.enable_checkbox.setChecked(enabled)
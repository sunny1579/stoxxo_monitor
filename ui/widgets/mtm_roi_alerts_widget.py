"""
MTM & ROI Alerts Widget
Section for configuring MTM and ROI% threshold alerts per user
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QCheckBox, QTableWidget, QTableWidgetItem, 
                              QGroupBox, QHeaderView, QLineEdit)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator


class MTMROIAlertsWidget(QGroupBox):
    """
    Widget for configuring MTM and ROI% alert thresholds per user
    """
    
    # Signal
    config_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("")
        self._init_ui()
        
        # Store user data
        self._user_thresholds = {}  # {user_alias: {mtm_above, mtm_below, roi_above, roi_below}}
    
    def _init_ui(self):
        """Initialize the UI"""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        # Enable checkbox
        self.enable_checkbox = QCheckBox("Enable TG alerts for MTM and ROI %")
        self.enable_checkbox.setChecked(True)
        self.enable_checkbox.setStyleSheet(self._get_checkbox_style())
        self.enable_checkbox.stateChanged.connect(self._on_config_changed)
        main_layout.addWidget(self.enable_checkbox)
        
        main_layout.addSpacing(8)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "user\nalias",
            "MTM\nabove",
            "MTM\nbelow",
            "ROI%\nabove",
            "ROI%\nbelow"
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
        for col in range(5):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 120)  # user alias
        self.table.setColumnWidth(1, 100)  # MTM above
        self.table.setColumnWidth(2, 100)  # MTM below
        self.table.setColumnWidth(3, 100)  # ROI% above
        self.table.setColumnWidth(4, 100)  # ROI% below
        
        # Prevent column reordering
        header.setSectionsMovable(False)
        
        main_layout.addWidget(self.table)
        
        # Note label
        note_label = QLabel("Note: User aliases fetched from Monitoring tab")
        note_label.setStyleSheet("""
            color: #a0aec0;
            font-size: 10px;
            font-style: italic;
        """)
        main_layout.addWidget(note_label)
        
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
        
        # Validator for numeric input (allows negative, positive, decimal, empty)
        validator = QDoubleValidator()
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
            
            # Get saved values for this user if they exist
            saved = current_values.get(user_alias, {})
            
            # MTM above
            mtm_above_input = self._create_editable_cell(saved.get('mtm_above', ''))
            self.table.setCellWidget(row, 1, mtm_above_input)
            
            # MTM below
            mtm_below_input = self._create_editable_cell(saved.get('mtm_below', ''))
            self.table.setCellWidget(row, 2, mtm_below_input)
            
            # ROI% above
            roi_above_input = self._create_editable_cell(saved.get('roi_above', ''))
            self.table.setCellWidget(row, 3, roi_above_input)
            
            # ROI% below
            roi_below_input = self._create_editable_cell(saved.get('roi_below', ''))
            self.table.setCellWidget(row, 4, roi_below_input)
        
        # Adjust row heights
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 35)
    
    def get_all_thresholds(self):
        """
        Get all threshold values for all users
        
        Returns:
            Dict: {user_alias: {mtm_above, mtm_below, roi_above, roi_below}}
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
            mtm_above_widget = self.table.cellWidget(row, 1)
            mtm_below_widget = self.table.cellWidget(row, 2)
            roi_above_widget = self.table.cellWidget(row, 3)
            roi_below_widget = self.table.cellWidget(row, 4)
            
            thresholds[user_alias] = {
                'mtm_above': mtm_above_widget.text() if mtm_above_widget else '',
                'mtm_below': mtm_below_widget.text() if mtm_below_widget else '',
                'roi_above': roi_above_widget.text() if roi_above_widget else '',
                'roi_below': roi_below_widget.text() if roi_below_widget else ''
            }
        
        return thresholds
    
    def set_user_thresholds(self, user_alias, thresholds):
        """
        Set thresholds for a specific user
        
        Args:
            user_alias: User alias string
            thresholds: Dict with keys: mtm_above, mtm_below, roi_above, roi_below
        """
        
        # Find row for this user
        found = False
        for row in range(self.table.rowCount()):
            alias_item = self.table.item(row, 0)
            if alias_item and alias_item.text() == user_alias:
                found = True
                
                # BLOCK SIGNALS while setting all values to prevent intermediate saves
                mtm_above = self.table.cellWidget(row, 1)
                mtm_below = self.table.cellWidget(row, 2)
                roi_above = self.table.cellWidget(row, 3)
                roi_below = self.table.cellWidget(row, 4)
                
                # Block all widgets
                if mtm_above:
                    mtm_above.blockSignals(True)
                if mtm_below:
                    mtm_below.blockSignals(True)
                if roi_above:
                    roi_above.blockSignals(True)
                if roi_below:
                    roi_below.blockSignals(True)
                
                # Set values
                if mtm_above:
                    value = str(thresholds.get('mtm_above', ''))
                    mtm_above.setText(value)
                
                if mtm_below:
                    value = str(thresholds.get('mtm_below', ''))
                    mtm_below.setText(value)
                
                if roi_above:
                    value = str(thresholds.get('roi_above', ''))
                    roi_above.setText(value)
                
                if roi_below:
                    value = str(thresholds.get('roi_below', ''))
                    roi_below.setText(value)
                
                # Unblock all widgets
                if mtm_above:
                    mtm_above.blockSignals(False)
                if mtm_below:
                    mtm_below.blockSignals(False)
                if roi_above:
                    roi_above.blockSignals(False)
                if roi_below:
                    roi_below.blockSignals(False)
                
                break
        
    def is_enabled(self):
        """Check if MTM/ROI alerts are enabled"""
        return self.enable_checkbox.isChecked()
    
    def set_enabled(self, enabled):
        """Set enabled state"""
        self.enable_checkbox.setChecked(enabled)
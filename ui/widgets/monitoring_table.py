"""
Monitoring Table Widget
Main table displaying all users and their options positions
"""
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.formatters import (format_pnl, format_quantity, format_roi, format_margin,
                              format_utilised_percent, get_pnl_color, get_quantity_color)


class MonitoringTable(QTableWidget):
    """
    Table widget for displaying user quantity monitoring data
    """
    
    # Column definitions (in display order)
    COLUMNS = [
        "User Alias",
        "User ID",
        "Live P&L",
        "ROI %",
        "Available Margin",
        "Utilized Margin",
        "Utilised %",
        "Call Sell Qty",
        "Call Buy Qty",
        "Calls Net",
        "Put Sell Qty",
        "Put Buy Qty",
        "Puts Net",
        "Quantity Imparity"
    ]
    
    # Column indices
    COL_USER_ALIAS = 0
    COL_USER_ID = 1
    COL_PNL = 2
    COL_ROI = 3
    COL_AVAILABLE_MARGIN = 4
    COL_UTILIZED_MARGIN = 5
    COL_UTILISED_PERCENT = 6
    COL_CALL_SELL = 7
    COL_CALL_BUY = 8
    COL_CALLS_NET = 9
    COL_PUT_SELL = 10
    COL_PUT_BUY = 11
    COL_PUTS_NET = 12
    COL_IMPARITY = 13
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # P&L visibility state
        self.pnl_hidden = False
        
        # Store previous data for comparison
        self._previous_data = {}
        
        self._setup_table()
    
    def _setup_table(self):
        """Initialize table structure and styling"""
        # Set column count
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        
        # Table properties
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        
        # Prevent text from spilling over - wrap within cell boundaries
        self.setWordWrap(True)
        
        # SORTING DISABLED - Causes crashes with real-time updates
        self.setSortingEnabled(False)
        
        # Column widths
        header = self.horizontalHeader()
        
        # Enable column dragging (reordering)
        header.setSectionsMovable(True)
        header.setDragEnabled(True)
        header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        
        # Disable sort indicators (no sorting)
        header.setSortIndicatorShown(False)
        
        # Make header non-clickable for sorting
        header.setSectionsClickable(False)
        
        # Enable word wrap in header as well
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        # Note: QHeaderView doesn't have setWordWrap, so we'll use TextElideMode
        # to truncate with ellipsis if text is too long
        header.setTextElideMode(Qt.TextElideMode.ElideRight)
        
        # Configure column resize modes
        # Use Interactive mode to allow manual resizing by dragging column edges
        # ALL columns are now manually resizable
        header.setSectionResizeMode(self.COL_USER_ALIAS, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_USER_ID, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_PNL, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_ROI, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_AVAILABLE_MARGIN, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_UTILIZED_MARGIN, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_UTILISED_PERCENT, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_CALL_SELL, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_CALL_BUY, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_CALLS_NET, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_PUT_SELL, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_PUT_BUY, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_PUTS_NET, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(self.COL_IMPARITY, QHeaderView.ResizeMode.Interactive)
        
        # Set initial/default column widths (users can resize from these)
        self.setColumnWidth(self.COL_USER_ALIAS, 150)
        self.setColumnWidth(self.COL_USER_ID, 100)
        self.setColumnWidth(self.COL_PNL, 120)
        self.setColumnWidth(self.COL_ROI, 100)
        self.setColumnWidth(self.COL_AVAILABLE_MARGIN, 150)
        self.setColumnWidth(self.COL_UTILIZED_MARGIN, 150)
        self.setColumnWidth(self.COL_UTILISED_PERCENT, 100)
        self.setColumnWidth(self.COL_CALL_SELL, 120)
        self.setColumnWidth(self.COL_CALL_BUY, 120)
        self.setColumnWidth(self.COL_CALLS_NET, 100)
        self.setColumnWidth(self.COL_PUT_SELL, 120)
        self.setColumnWidth(self.COL_PUT_BUY, 120)
        self.setColumnWidth(self.COL_PUTS_NET, 100)
        self.setColumnWidth(self.COL_IMPARITY, 120)
        
        # Row height
        self.verticalHeader().setDefaultSectionSize(35)
    
    def update_data(self, summaries):
        """
        Update table with new data
        Preserves scroll position and only updates changed cells
        
        Args:
            summaries: List of OptionsPositionSummary objects
        """
        # Sorting is ALWAYS disabled - we only sort on manual header clicks
        # This prevents any issues with Qt's automatic sorting
        
        # Save scroll position
        scrollbar = self.verticalScrollBar()
        scroll_position = scrollbar.value()
        
        # Build lookup by user_id for new data
        new_data = {s.user_id: s for s in summaries}

        # Check if we need to rebuild table (different users, count, or hidden state changed)
        need_rebuild = (
            len(summaries) != self.rowCount() or
            set(new_data.keys()) != set(self._previous_data.keys())
        )

        # Also force rebuild when pnl_hidden changed since last draw
        if not hasattr(self, '_last_pnl_hidden'):
            self._last_pnl_hidden = self.pnl_hidden
        if self._last_pnl_hidden != self.pnl_hidden:
            need_rebuild = True
            self._last_pnl_hidden = self.pnl_hidden
        
        if need_rebuild:
            # Full rebuild needed
            self.setRowCount(0)
            for summary in summaries:
                self._add_row(summary)
        else:
            # Update by position — order is stable; rebuild is triggered
            # whenever the user set changes, so row N always == summaries[N].
            for row in range(self.rowCount()):
                if row < len(summaries):
                    self._update_row(row, summaries[row])
        
        # Store current data for next comparison
        self._previous_data = new_data
        
        # Restore scroll position
        scrollbar.setValue(scroll_position)
    
    def _add_row(self, summary):
        """
        Add a row to the table
        
        Args:
            summary: OptionsPositionSummary object
        """
        row = self.rowCount()
        self.insertRow(row)
        
        # User Alias (masked when hidden)
        alias_text = "●●●●●" if self.pnl_hidden else summary.user_alias
        self._set_cell(row, self.COL_USER_ALIAS, alias_text, align_center=False)

        # User ID (masked when hidden)
        uid_text = "●●●●" if self.pnl_hidden else (summary.user_id or "Default")
        self._set_cell(row, self.COL_USER_ID, uid_text, align_center=False)
        
        # Live P&L (colored) - check if hidden
        if self.pnl_hidden:
            pnl_text = "xxxx"
            pnl_color = None
        else:
            pnl_text = format_pnl(summary.live_pnl)
            pnl_color = get_pnl_color(summary.live_pnl)
        self._set_cell(row, self.COL_PNL, pnl_text, color=pnl_color, bold=True)
        
        # ROI % (colored, hidden if P&L is hidden)
        if self.pnl_hidden:
            roi_text = "xxxx"
            roi_color = None
        else:
            roi_text = format_roi(summary.roi_percent)
            roi_color = get_pnl_color(summary.roi_percent)  # Same color logic as P&L
        self._set_cell(row, self.COL_ROI, roi_text, color=roi_color, bold=True)
        
        # Available Margin
        margin_avail_text = format_margin(summary.available_margin)
        self._set_cell(row, self.COL_AVAILABLE_MARGIN, margin_avail_text)
        
        # Utilized Margin
        margin_util_text = format_margin(summary.utilized_margin)
        self._set_cell(row, self.COL_UTILIZED_MARGIN, margin_util_text)
        
        # Utilised %
        utilised_pct_text = format_utilised_percent(summary.utilised_percent)
        self._set_cell(row, self.COL_UTILISED_PERCENT, utilised_pct_text)
        
        # Call Sell Qty (negative, red)
        call_sell_text = format_quantity(summary.call_sell_qty)
        call_sell_color = get_quantity_color(summary.call_sell_qty)
        self._set_cell(row, self.COL_CALL_SELL, call_sell_text, color=call_sell_color)
        
        # Call Buy Qty (positive, green)
        call_buy_text = format_quantity(summary.call_buy_qty)
        call_buy_color = get_quantity_color(summary.call_buy_qty)
        self._set_cell(row, self.COL_CALL_BUY, call_buy_text, color=call_buy_color)
        
        # Calls Net (colored by value)
        calls_net_text = format_quantity(summary.calls_net)
        calls_net_color = get_quantity_color(summary.calls_net)
        self._set_cell(row, self.COL_CALLS_NET, calls_net_text, color=calls_net_color, bold=True)
        
        # Put Sell Qty (negative, red)
        put_sell_text = format_quantity(summary.put_sell_qty)
        put_sell_color = get_quantity_color(summary.put_sell_qty)
        self._set_cell(row, self.COL_PUT_SELL, put_sell_text, color=put_sell_color)
        
        # Put Buy Qty (positive, green)
        put_buy_text = format_quantity(summary.put_buy_qty)
        put_buy_color = get_quantity_color(summary.put_buy_qty)
        self._set_cell(row, self.COL_PUT_BUY, put_buy_text, color=put_buy_color)
        
        # Puts Net (colored by value)
        puts_net_text = format_quantity(summary.puts_net)
        puts_net_color = get_quantity_color(summary.puts_net)
        self._set_cell(row, self.COL_PUTS_NET, puts_net_text, color=puts_net_color, bold=True)
        
        # Quantity Imparity (orb indicator)
        self._set_imparity_cell(row, summary.imparity_status)
    
    def _update_row(self, row, summary):
        """
        Update an existing row with new data (only updates changed cells)
        More efficient than rebuilding the entire row

        Args:
            row: Row index
            summary: OptionsPositionSummary object
        """
        # Update user alias and user ID (respecting hidden state)
        alias_text = "●●●●●" if self.pnl_hidden else summary.user_alias
        uid_text   = "●●●●"  if self.pnl_hidden else (summary.user_id or "Default")
        alias_item = self.item(row, self.COL_USER_ALIAS)
        uid_item   = self.item(row, self.COL_USER_ID)
        if alias_item and alias_item.text() != alias_text:
            self._set_cell(row, self.COL_USER_ALIAS, alias_text, align_center=False)
        if uid_item and uid_item.text() != uid_text:
            self._set_cell(row, self.COL_USER_ID, uid_text, align_center=False)

        # Update P&L if changed (respecting hidden state)
        if self.pnl_hidden:
            pnl_text = "xxxx"
            pnl_color = None
        else:
            pnl_text = format_pnl(summary.live_pnl)
            pnl_color = get_pnl_color(summary.live_pnl)
        
        pnl_item = self.item(row, self.COL_PNL)
        if pnl_item and pnl_item.text() != pnl_text:
            self._set_cell(row, self.COL_PNL, pnl_text, color=pnl_color, bold=True)
        
        # Update ROI % if changed (respecting hidden state)
        if self.pnl_hidden:
            roi_text = "xxxx"
            roi_color = None
        else:
            roi_text = format_roi(summary.roi_percent)
            roi_color = get_pnl_color(summary.roi_percent)
        
        roi_item = self.item(row, self.COL_ROI)
        if roi_item and roi_item.text() != roi_text:
            self._set_cell(row, self.COL_ROI, roi_text, color=roi_color, bold=True)
        
        # Update Available Margin if changed
        margin_avail_text = format_margin(summary.available_margin)
        margin_avail_item = self.item(row, self.COL_AVAILABLE_MARGIN)
        if margin_avail_item and margin_avail_item.text() != margin_avail_text:
            self._set_cell(row, self.COL_AVAILABLE_MARGIN, margin_avail_text)
        
        # Update Utilized Margin if changed
        margin_util_text = format_margin(summary.utilized_margin)
        margin_util_item = self.item(row, self.COL_UTILIZED_MARGIN)
        if margin_util_item and margin_util_item.text() != margin_util_text:
            self._set_cell(row, self.COL_UTILIZED_MARGIN, margin_util_text)
        
        # Update Utilised % if changed
        utilised_pct_text = format_utilised_percent(summary.utilised_percent)
        utilised_pct_item = self.item(row, self.COL_UTILISED_PERCENT)
        if utilised_pct_item and utilised_pct_item.text() != utilised_pct_text:
            self._set_cell(row, self.COL_UTILISED_PERCENT, utilised_pct_text)
        
        # Update Call Sell Qty if changed
        call_sell_text = format_quantity(summary.call_sell_qty)
        call_sell_item = self.item(row, self.COL_CALL_SELL)
        if call_sell_item and call_sell_item.text() != call_sell_text:
            call_sell_color = get_quantity_color(summary.call_sell_qty)
            self._set_cell(row, self.COL_CALL_SELL, call_sell_text, color=call_sell_color)
        
        # Update Call Buy Qty if changed
        call_buy_text = format_quantity(summary.call_buy_qty)
        call_buy_item = self.item(row, self.COL_CALL_BUY)
        if call_buy_item and call_buy_item.text() != call_buy_text:
            call_buy_color = get_quantity_color(summary.call_buy_qty)
            self._set_cell(row, self.COL_CALL_BUY, call_buy_text, color=call_buy_color)
        
        # Update Calls Net if changed
        calls_net_text = format_quantity(summary.calls_net)
        calls_net_item = self.item(row, self.COL_CALLS_NET)
        if calls_net_item and calls_net_item.text() != calls_net_text:
            calls_net_color = get_quantity_color(summary.calls_net)
            self._set_cell(row, self.COL_CALLS_NET, calls_net_text, color=calls_net_color, bold=True)
        
        # Update Put Sell Qty if changed
        put_sell_text = format_quantity(summary.put_sell_qty)
        put_sell_item = self.item(row, self.COL_PUT_SELL)
        if put_sell_item and put_sell_item.text() != put_sell_text:
            put_sell_color = get_quantity_color(summary.put_sell_qty)
            self._set_cell(row, self.COL_PUT_SELL, put_sell_text, color=put_sell_color)
        
        # Update Put Buy Qty if changed
        put_buy_text = format_quantity(summary.put_buy_qty)
        put_buy_item = self.item(row, self.COL_PUT_BUY)
        if put_buy_item and put_buy_item.text() != put_buy_text:
            put_buy_color = get_quantity_color(summary.put_buy_qty)
            self._set_cell(row, self.COL_PUT_BUY, put_buy_text, color=put_buy_color)
        
        # Update Puts Net if changed
        puts_net_text = format_quantity(summary.puts_net)
        puts_net_item = self.item(row, self.COL_PUTS_NET)
        if puts_net_item and puts_net_item.text() != puts_net_text:
            puts_net_color = get_quantity_color(summary.puts_net)
            self._set_cell(row, self.COL_PUTS_NET, puts_net_text, color=puts_net_color, bold=True)
        
        # Update Imparity status if needed (compare widget background color)
        # For simplicity, always update this (it's a widget, not an item)
        self._set_imparity_cell(row, summary.imparity_status)
    
    def _set_cell(self, row, col, text, color=None, bold=False, align_center=True):
        """
        Set cell value with styling
        
        Args:
            row: Row index
            col: Column index
            text: Cell text
            color: Text color (hex string)
            bold: Make text bold
            align_center: Center align text
        """
        item = QTableWidgetItem(str(text))
        
        # Alignment
        if align_center:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        # Color
        if color:
            item.setForeground(QColor(color))
        
        # Bold
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        
        # Store numeric value for proper sorting
        # Try to convert to float for numeric columns
        try:
            # Remove formatting characters like +, -, %, commas
            clean_text = str(text).replace('+', '').replace('%', '').replace(',', '')
            numeric_value = float(clean_text)
            item.setData(Qt.ItemDataRole.UserRole, numeric_value)
        except (ValueError, AttributeError):
            # Not a number, store as string for alphabetical sorting
            item.setData(Qt.ItemDataRole.UserRole, str(text))
        
        # Prevent text overflow - will show ellipsis (...) if too long
        # This works in conjunction with setWordWrap for best results
        
        self.setItem(row, col, item)
    
    def _set_imparity_cell(self, row, status):
        """
        Set imparity indicator cell with colored orb
        
        Args:
            row: Row index
            status: 'green' or 'red'
        """
        # Create widget for visual display
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create orb label
        orb = QLabel()
        if status == 'green':
            orb.setText("  ")  # Empty text, just the colored circle
            orb.setStyleSheet("background-color: #48bb78; border-radius: 10px; min-width: 20px; min-height: 20px;")
        else:
            orb.setText("  ")  # Empty text, just the colored circle
            orb.setStyleSheet("background-color: #f56565; border-radius: 10px; min-width: 20px; min-height: 20px;")
        
        layout.addWidget(orb)
        
        # Set widget in cell
        self.setCellWidget(row, self.COL_IMPARITY, widget)
    
    def clear_data(self):
        """Clear all data from table"""
        self.setRowCount(0)


if __name__ == "__main__":
    # Test the table
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from models.position_summary import OptionsPositionSummary
    from datetime import datetime
    
    app = QApplication(sys.argv)
    
    # Load stylesheet
    try:
        stylesheet_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'styles', 'dark_theme.qss'
        )
        with open(stylesheet_path, 'r') as f:
            app.setStyleSheet(f.read())
    except Exception as e:
        print("Could not load stylesheet: %s" % str(e))
    
    # Create window
    window = QMainWindow()
    window.setWindowTitle("Monitoring Table Test")
    window.setGeometry(100, 100, 1200, 600)
    
    # Create table
    table = MonitoringTable()
    window.setCentralWidget(table)
    
    # Test data
    test_summaries = [
        OptionsPositionSummary(
            user_id="",
            user_alias="Trader01",
            live_pnl=2350.50,
            call_sell_qty=-50,
            call_buy_qty=20,
            put_sell_qty=-30,
            put_buy_qty=15,
            puts_net=-15,
            calls_net=-30,
            imparity_status='red',
            last_updated=datetime.now()
        ),
        OptionsPositionSummary(
            user_id="USER001",
            user_alias="Alpha200",
            live_pnl=-1480.25,
            call_sell_qty=-30,
            call_buy_qty=50,
            put_sell_qty=-90,
            put_buy_qty=40,
            puts_net=-50,
            calls_net=20,
            imparity_status='red',
            last_updated=datetime.now()
        ),
        OptionsPositionSummary(
            user_id="USER002",
            user_alias="StockGuru",
            live_pnl=3720.00,
            call_sell_qty=-80,
            call_buy_qty=80,
            put_sell_qty=-60,
            put_buy_qty=60,
            puts_net=0,
            calls_net=0,
            imparity_status='green',
            last_updated=datetime.now()
        ),
    ]
    
    # Update table with test data
    table.update_data(test_summaries)
    
    window.show()
    sys.exit(app.exec())
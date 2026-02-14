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

from utils.formatters import format_pnl, format_quantity, get_pnl_color, get_quantity_color


class MonitoringTable(QTableWidget):
    """
    Table widget for displaying user quantity monitoring data
    """
    
    # Column definitions
    COLUMNS = [
        "User Alias",
        "Live P&L",
        "Call Sell Qty",
        "Call Buy Qty",
        "Put Sell Qty",
        "Put Buy Qty",
        "Puts Net",
        "Calls Net",
        "Quantity Imparity"
    ]
    
    # Column indices
    COL_USER = 0
    COL_PNL = 1
    COL_CALL_SELL = 2
    COL_CALL_BUY = 3
    COL_PUT_SELL = 4
    COL_PUT_BUY = 5
    COL_PUTS_NET = 6
    COL_CALLS_NET = 7
    COL_IMPARITY = 8
    
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
        
        # Column widths
        header = self.horizontalHeader()
        header.setSectionResizeMode(self.COL_USER, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COL_PNL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_CALL_SELL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_CALL_BUY, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_PUT_SELL, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_PUT_BUY, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_PUTS_NET, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_CALLS_NET, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_IMPARITY, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(self.COL_IMPARITY, 100)
        
        # Row height
        self.verticalHeader().setDefaultSectionSize(35)
    
    def update_data(self, summaries):
        """
        Update table with new data
        Preserves scroll position and only updates changed cells
        
        Args:
            summaries: List of OptionsPositionSummary objects
        """
        # Save scroll position
        scrollbar = self.verticalScrollBar()
        scroll_position = scrollbar.value()
        
        # Build lookup by user_id for new data
        new_data = {s.user_id: s for s in summaries}
        
        # Check if we need to rebuild table (different users or count)
        need_rebuild = (
            len(summaries) != self.rowCount() or
            set(new_data.keys()) != set(self._previous_data.keys())
        )
        
        if need_rebuild:
            # Full rebuild needed
            self.setRowCount(0)
            for summary in summaries:
                self._add_row(summary)
        else:
            # Update existing rows (more efficient)
            for row in range(self.rowCount()):
                user_alias_item = self.item(row, self.COL_USER)
                if not user_alias_item:
                    continue
                
                # Find matching summary by checking user_alias
                matching_summary = None
                for summary in summaries:
                    if summary.user_alias == user_alias_item.text():
                        matching_summary = summary
                        break
                
                if matching_summary:
                    self._update_row(row, matching_summary)
        
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
        
        # User Alias
        self._set_cell(row, self.COL_USER, summary.user_alias, align_center=False)
        
        # Live P&L (colored) - check if hidden
        if self.pnl_hidden:
            pnl_text = "xxxx"
            pnl_color = None
        else:
            pnl_text = format_pnl(summary.live_pnl)
            pnl_color = get_pnl_color(summary.live_pnl)
        self._set_cell(row, self.COL_PNL, pnl_text, color=pnl_color, bold=True)
        
        # Call Sell Qty (negative, red)
        call_sell_text = format_quantity(summary.call_sell_qty)
        call_sell_color = get_quantity_color(summary.call_sell_qty)
        self._set_cell(row, self.COL_CALL_SELL, call_sell_text, color=call_sell_color)
        
        # Call Buy Qty (positive, green)
        call_buy_text = format_quantity(summary.call_buy_qty)
        call_buy_color = get_quantity_color(summary.call_buy_qty)
        self._set_cell(row, self.COL_CALL_BUY, call_buy_text, color=call_buy_color)
        
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
        
        # Calls Net (colored by value)
        calls_net_text = format_quantity(summary.calls_net)
        calls_net_color = get_quantity_color(summary.calls_net)
        self._set_cell(row, self.COL_CALLS_NET, calls_net_text, color=calls_net_color, bold=True)
        
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
        
        # Update Calls Net if changed
        calls_net_text = format_quantity(summary.calls_net)
        calls_net_item = self.item(row, self.COL_CALLS_NET)
        if calls_net_item and calls_net_item.text() != calls_net_text:
            calls_net_color = get_quantity_color(summary.calls_net)
            self._set_cell(row, self.COL_CALLS_NET, calls_net_text, color=calls_net_color, bold=True)
        
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
        # Create widget for cell
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create orb label
        orb = QLabel()
        if status == 'green':
            orb.setText("  ")  # Green circle (using Unicode)
            orb.setStyleSheet("background-color: #48bb78; border-radius: 10px; min-width: 20px; min-height: 20px;")
        else:
            orb.setText("  ")  # Red circle
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
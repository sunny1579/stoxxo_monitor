"""
Polling Service
Real-time data updates using QThread
"""
import logging
import time
from PyQt6.QtCore import QThread, pyqtSignal
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.position_tracker import OptionsPositionTracker


class PollingService(QThread):
    """
    Background polling service for real-time updates
    Runs in separate thread to avoid blocking UI
    """
    
    # Signals (emitted to UI)
    all_users_updated = pyqtSignal(list)  # List[OptionsPositionSummary]
    connection_status_changed = pyqtSignal(bool)  # True=connected, False=disconnected
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, stoxxo_client):
        super().__init__()
        self.client = stoxxo_client
        self.tracker = OptionsPositionTracker(stoxxo_client)
        self.logger = logging.getLogger(__name__)
        
        # Polling control
        self.interval_seconds = 1.0  # Default: 1 second
        self.is_running = False
        self._should_stop = False
        
        # Connection tracking
        self._last_connection_status = None
    
    def set_interval(self, seconds):
        """
        Set polling interval
        
        Args:
            seconds: Polling interval in seconds (0.5, 1, 2, 5, 10)
        """
        self.interval_seconds = max(0.5, seconds)  # Minimum 0.5 seconds
        self.logger.info("Polling interval set to %.1f seconds", self.interval_seconds)
    
    def stop(self):
        """Stop the polling service"""
        self.logger.info("Stopping polling service...")
        self._should_stop = True
        self.is_running = False
    
    def run(self):
        """
        Main polling loop (runs in separate thread)
        """
        self.logger.info("Polling service started")
        self.is_running = True
        self._should_stop = False
        
        while not self._should_stop:
            try:
                # Check connection
                is_connected = self._check_connection()
                
                if is_connected:
                    # Fetch data
                    summaries = self.tracker.get_all_users_summary()
                    
                    # Emit update signal
                    self.all_users_updated.emit(summaries)
                    
                    self.logger.debug("Polled data: %d users", len(summaries))
                else:
                    self.logger.warning("Not connected to Stoxxo Bridge")
                
            except Exception as e:
                self.logger.error("Polling error: %s", str(e))
                self.error_occurred.emit(str(e))
            
            # Wait for next interval
            time.sleep(self.interval_seconds)
        
        self.logger.info("Polling service stopped")
        self.is_running = False
    
    def _check_connection(self):
        """
        Check Stoxxo Bridge connection
        
        Returns:
            True if connected, False otherwise
        """
        try:
            is_connected = self.client.status.ping()
            
            # Emit status change if different from last check
            if is_connected != self._last_connection_status:
                self.connection_status_changed.emit(is_connected)
                self._last_connection_status = is_connected
                
                if is_connected:
                    self.logger.info("Connected to Stoxxo Bridge")
                else:
                    self.logger.warning("Disconnected from Stoxxo Bridge")
            
            return is_connected
            
        except Exception as e:
            self.logger.error("Connection check failed: %s", str(e))
            
            # Emit disconnected if we had connection before
            if self._last_connection_status != False:
                self.connection_status_changed.emit(False)
                self._last_connection_status = False
            
            return False


if __name__ == "__main__":
    # Test polling service
    from PyQt6.QtWidgets import QApplication
    from core.stoxxo_client import StoxxoClient
    from utils.logger import setup_logger
    
    # Setup logging
    logger = setup_logger()
    
    print("Testing Polling Service")
    print("=" * 50)
    
    # Create Qt application (required for QThread)
    app = QApplication(sys.argv)
    
    try:
        # Create Stoxxo client
        client = StoxxoClient()
        
        # Create polling service
        poller = PollingService(client)
        
        # Connect signals
        def on_users_updated(summaries):
            print("\n[UPDATE] Received %d users:" % len(summaries))
            for summary in summaries:
                print("  %s: P&L=%.2f, Calls Net=%d, Puts Net=%d, Status=%s" % (
                    summary.user_alias,
                    summary.live_pnl,
                    summary.calls_net,
                    summary.puts_net,
                    summary.imparity_status
                ))
        
        def on_connection_changed(is_connected):
            status = "CONNECTED" if is_connected else "DISCONNECTED"
            print("\n[CONNECTION] %s" % status)
        
        def on_error(error_msg):
            print("\n[ERROR] %s" % error_msg)
        
        poller.all_users_updated.connect(on_users_updated)
        poller.connection_status_changed.connect(on_connection_changed)
        poller.error_occurred.connect(on_error)
        
        # Set interval
        poller.set_interval(2.0)  # 2 seconds for testing
        
        # Start polling
        print("\nStarting polling service (press Ctrl+C to stop)...")
        poller.start()
        
        # Run application
        sys.exit(app.exec())
        
    except KeyboardInterrupt:
        print("\n\nStopping...")
        poller.stop()
        poller.wait()
    except Exception as e:
        print("Error: %s" % str(e))
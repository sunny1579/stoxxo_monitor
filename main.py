
"""
Stoxxo User Quantity Monitoring Tool
Main application entry point
"""
import sys
import os
from PyQt6.QtWidgets import QApplication

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from utils.logger import setup_logger


def main():
    """Main application entry point"""
    
    # Setup logging
    logger = setup_logger(
        name="stoxxo_monitor",
        log_file="stoxxo_monitor.log",
        level="INFO"
    )
    
    logger.info("=" * 60)
    logger.info("Stoxxo User Quantity Monitoring Tool v1.0.0")
    logger.info("=" * 60)
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Stoxxo Monitor")
    app.setOrganizationName("Stoxxo")
    
    # Load stylesheet
    try:
        # Try ui/styles first
        stylesheet_path = os.path.join(
            os.path.dirname(__file__),
            'ui',
            'styles',
            'dark_theme.qss'
        )
        
        # If not found, try root styles folder
        if not os.path.exists(stylesheet_path):
            stylesheet_path = os.path.join(
                os.path.dirname(__file__),
                'styles',
                'dark_theme.qss'
            )
        
        with open(stylesheet_path, 'r') as f:
            stylesheet = f.read()
            app.setStyleSheet(stylesheet)
            logger.info("Dark theme loaded successfully from: %s", stylesheet_path)
    except Exception as e:
        logger.error("Failed to load stylesheet: %s", str(e))
    
    # Create and show main window
    try:
        window = MainWindow()
        window.show()
        logger.info("Main window displayed")
    except Exception as e:
        logger.error("Failed to create main window: %s", str(e))
        return 1
    
    # Run application event loop
    logger.info("Application started")
    exit_code = app.exec()
    
    logger.info("Application exited with code: %d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
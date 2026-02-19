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


def resource_path(relative_path):
    """
    Get absolute path to a resource file.
    Works both in development (normal python) and when packaged as PyInstaller exe.
    
    In dev:    returns path relative to this file
    In exe:    returns path inside the temp _MEIPASS folder PyInstaller creates
    """
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller exe
        return os.path.join(sys._MEIPASS, relative_path)
    # Running as normal python script
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


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

    # Load stylesheet using resource_path so it works in exe too
    try:
        stylesheet_path = resource_path(os.path.join('ui', 'styles', 'dark_theme.qss'))

        if not os.path.exists(stylesheet_path):
            # Fallback to root styles folder
            stylesheet_path = resource_path(os.path.join('styles', 'dark_theme.qss'))

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
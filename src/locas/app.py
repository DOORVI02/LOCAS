"""LOCAS Application Bootstrap."""

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from locas.config import Config
from locas.core.database import DatabaseManager
from locas.gui.main_window import MainWindow


def run_application() -> int:
    """Initialize and run the LOCAS application.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    # Load configuration
    config = Config.load()

    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(config.app_name)
    app.setApplicationVersion(config.app_version)
    app.setOrganizationName("LOCAS")

    # Initialize database connection
    try:
        db_manager = DatabaseManager(config)
        db_manager.initialize()
    except Exception as e:
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None,
            "Database Error",
            f"Failed to connect to database:\n{e}\n\nPlease check your configuration.",
        )
        return 1

    # Create and show main window
    window = MainWindow(config, db_manager)
    window.show()

    # Run event loop
    exit_code = app.exec()

    # Cleanup
    db_manager.close()

    return exit_code

"""
app.py
------
Application bootstrap for DeskGuard.

Wires together configuration, logging, and the GUI. Import and
call `run()` from the root-level main.py to launch the app.

Owned primarily by: Sadurthiya (integration), with input from all members
"""

import sys

from PyQt5.QtWidgets import QApplication
from loguru import logger

from src import config, utils
from src.gui import MainWindow


def run() -> None:
    """Initialize logging and launch the DeskGuard GUI application."""
    utils.setup_logger()
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)

    window = MainWindow()
    window.show()

    exit_code = app.exec_()
    logger.info(f"{config.APP_NAME} exited with code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    run()
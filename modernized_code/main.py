#!/usr/bin/env python3
"""
Trader Bot - Main Application

This is the entry point for the Trader Bot application, which provides a GUI
for cryptocurrency trading with automated strategies on Binance.
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QSplitter, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt

from ui.fake_account_tab import FakeAccountTab
from ui.binance_account_tab import BinanceAccountTab
from ui.history_tab import HistoryTab
from ui.logger_widget import LoggerWidget
from config import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TraderBotApp(QMainWindow):
    """Main application window for Trader Bot."""
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.config = load_config()
        
        # Set up the main window
        self.setWindowTitle("Trader Bot")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create main splitter
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Create tab widget for main content
        self.tabs = QTabWidget()
        
        # Create tabs
        self.fake_account_tab = FakeAccountTab(self.config)
        self.binance_account_tab = BinanceAccountTab(self.config)
        self.history_tab = HistoryTab(self.config)
        
        # Add tabs to widget
        self.tabs.addTab(self.fake_account_tab, "Fake Account Test")
        self.tabs.addTab(self.binance_account_tab, "Binance Account")
        self.tabs.addTab(self.history_tab, "History Test")
        
        # Create logger widget
        self.logger_widget = LoggerWidget()
        
        # Add widgets to splitter
        self.main_splitter.addWidget(self.tabs)
        self.main_splitter.addWidget(self.logger_widget)
        
        # Set splitter sizes
        self.main_splitter.setSizes([800, 400])
        
        # Set central widget
        self.setCentralWidget(self.main_splitter)
        
        logger.info("Trader Bot application initialized")
    
    def closeEvent(self, event):
        """Handle application close event."""
        logger.info("Shutting down Trader Bot application")
        
        # Clean up resources
        self.fake_account_tab.cleanup()
        self.binance_account_tab.cleanup()
        self.history_tab.cleanup()
        
        event.accept()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    window = TraderBotApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

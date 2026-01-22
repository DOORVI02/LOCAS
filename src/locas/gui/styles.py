"""PyQt6 stylesheet definitions for LOCAS."""


class Styles:
    """Application stylesheet definitions.
    
    Provides consistent styling across all GUI components.
    Uses a professional blue color scheme suitable for institutional use.
    """
    
    # Color palette
    PRIMARY = "#1976D2"          # Blue
    PRIMARY_DARK = "#1565C0"     # Darker blue
    PRIMARY_LIGHT = "#42A5F5"    # Lighter blue
    SECONDARY = "#424242"        # Dark gray
    SUCCESS = "#388E3C"          # Green
    WARNING = "#F57C00"          # Orange
    ERROR = "#D32F2F"            # Red
    
    BACKGROUND = "#FAFAFA"       # Light gray background
    SURFACE = "#FFFFFF"          # White surface
    TEXT_PRIMARY = "#212121"     # Almost black
    TEXT_SECONDARY = "#757575"   # Gray text
    BORDER = "#E0E0E0"           # Light border
    
    # Main application style
    MAIN_STYLE = f"""
        QMainWindow {{
            background-color: {BACKGROUND};
        }}
        
        QWidget {{
            font-family: "Segoe UI", "SF Pro Display", Arial, sans-serif;
            font-size: 14px;
            color: {TEXT_PRIMARY};
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {PRIMARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 500;
            min-width: 80px;
        }}
        
        QPushButton:hover {{
            background-color: {PRIMARY_DARK};
        }}
        
        QPushButton:pressed {{
            background-color: {PRIMARY_LIGHT};
        }}
        
        QPushButton:disabled {{
            background-color: #BDBDBD;
            color: #9E9E9E;
        }}
        
        QPushButton.secondary {{
            background-color: {SURFACE};
            color: {PRIMARY};
            border: 1px solid {PRIMARY};
        }}
        
        QPushButton.secondary:hover {{
            background-color: #E3F2FD;
        }}
        
        QPushButton.danger {{
            background-color: {ERROR};
        }}
        
        QPushButton.danger:hover {{
            background-color: #C62828;
        }}
        
        /* Input fields */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 8px;
            selection-background-color: {PRIMARY_LIGHT};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border: 2px solid {PRIMARY};
        }}
        
        QLineEdit:disabled {{
            background-color: #F5F5F5;
            color: {TEXT_SECONDARY};
        }}
        
        /* ComboBox */
        QComboBox {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 4px;
            padding: 6px 12px;
            min-width: 120px;
        }}
        
        QComboBox:focus {{
            border: 2px solid {PRIMARY};
        }}
        
        QComboBox::drop-down {{
            border: none;
            padding-right: 8px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            selection-background-color: {PRIMARY_LIGHT};
        }}
        
        /* Tables */
        QTableWidget, QTableView {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            gridline-color: {BORDER};
            selection-background-color: #E3F2FD;
            selection-color: {TEXT_PRIMARY};
        }}
        
        QTableWidget::item, QTableView::item {{
            padding: 8px;
        }}
        
        QHeaderView::section {{
            background-color: #F5F5F5;
            color: {TEXT_PRIMARY};
            padding: 8px;
            border: none;
            border-bottom: 2px solid {BORDER};
            font-weight: 600;
        }}
        
        /* Labels */
        QLabel {{
            color: {TEXT_PRIMARY};
        }}
        
        QLabel.heading {{
            font-size: 24px;
            font-weight: 600;
            color: {TEXT_PRIMARY};
        }}
        
        QLabel.subheading {{
            font-size: 16px;
            color: {TEXT_SECONDARY};
        }}
        
        QLabel.error {{
            color: {ERROR};
        }}
        
        QLabel.success {{
            color: {SUCCESS};
        }}
        
        /* Group Box */
        QGroupBox {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 4px;
            margin-top: 16px;
            padding-top: 16px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {TEXT_SECONDARY};
            font-weight: 600;
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            border: 1px solid {BORDER};
            background-color: {SURFACE};
        }}
        
        QTabBar::tab {{
            background-color: {BACKGROUND};
            border: 1px solid {BORDER};
            border-bottom: none;
            padding: 8px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {SURFACE};
            border-bottom: 2px solid {PRIMARY};
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: #E3F2FD;
        }}
        
        /* Scrollbars */
        QScrollBar:vertical {{
            background-color: {BACKGROUND};
            width: 12px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: #BDBDBD;
            min-height: 30px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: #9E9E9E;
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {SURFACE};
            border-bottom: 1px solid {BORDER};
        }}
        
        QMenuBar::item {{
            padding: 8px 12px;
        }}
        
        QMenuBar::item:selected {{
            background-color: #E3F2FD;
        }}
        
        QMenu {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
        }}
        
        QMenu::item {{
            padding: 8px 24px;
        }}
        
        QMenu::item:selected {{
            background-color: #E3F2FD;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {SURFACE};
            border-top: 1px solid {BORDER};
        }}
        
        /* Tooltips */
        QToolTip {{
            background-color: {SECONDARY};
            color: white;
            border: none;
            padding: 4px 8px;
        }}
        
        /* Progress Bar */
        QProgressBar {{
            background-color: #E0E0E0;
            border: none;
            border-radius: 4px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {PRIMARY};
            border-radius: 4px;
        }}
        
        /* Splitter */
        QSplitter::handle {{
            background-color: {BORDER};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
    """
    
    # Login screen specific styles
    LOGIN_STYLE = f"""
        QWidget#loginContainer {{
            background-color: {SURFACE};
            border-radius: 8px;
        }}
        
        QLabel#appTitle {{
            font-size: 28px;
            font-weight: 700;
            color: {PRIMARY};
        }}
        
        QLabel#appSubtitle {{
            font-size: 14px;
            color: {TEXT_SECONDARY};
        }}
        
        QLineEdit#loginInput {{
            padding: 12px;
            font-size: 15px;
        }}
        
        QPushButton#loginButton {{
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
        }}
    """
    
    # Dashboard card styles
    DASHBOARD_CARD = f"""
        QFrame#dashboardCard {{
            background-color: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 16px;
        }}
        
        QFrame#dashboardCard:hover {{
            border-color: {PRIMARY};
        }}
        
        QLabel#cardTitle {{
            font-size: 14px;
            color: {TEXT_SECONDARY};
        }}
        
        QLabel#cardValue {{
            font-size: 32px;
            font-weight: 700;
            color: {TEXT_PRIMARY};
        }}
        
        QLabel#cardIcon {{
            font-size: 24px;
            color: {PRIMARY};
        }}
    """

    @classmethod
    def get_full_stylesheet(cls) -> str:
        """Get the complete application stylesheet.
        
        Returns:
            Combined stylesheet string.
        """
        return cls.MAIN_STYLE + cls.LOGIN_STYLE + cls.DASHBOARD_CARD

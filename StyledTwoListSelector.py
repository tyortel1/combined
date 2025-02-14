from PySide6.QtWidgets import (QWidget, QListWidget, QVBoxLayout, QLabel, 
                               QAbstractItemView, QFrame, QPushButton, QHBoxLayout,
                               QSpacerItem, QSizePolicy, QLineEdit)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette, QColor, QIcon

class TwoListSelector(QWidget):
    """
    A complete dual list selector widget with transfer buttons and search functionality.
    Provides a modern look with consistent styling and item filtering.
    """
    
    # Signal for when items are transferred
    items_transferred = Signal()  # Emitted whenever items are moved between lists
    
    def __init__(self, left_title="Available Items", right_title="Selected Items", parent=None):
        super().__init__(parent)
        self.setup_ui(left_title, right_title)
        
    def setup_ui(self, left_title, right_title):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Two-list selector horizontal layout
        lists_layout = QHBoxLayout()
        
        # Create left container
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add left title label
        left_label = QLabel(left_title)
        left_label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
                padding: 5px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
        """)
        
        # Search input for left side
        self.left_search_input = QLineEdit()
        self.left_search_input.setPlaceholderText(f"Search {left_title.lower()}...")
        self.left_search_input.textChanged.connect(self.filter_left_items)
        self.left_search_input.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 1px solid #3498db;
            }
        """)
        
        # Create left list
        self.left_list = QListWidget()
        self.left_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.left_list.setFrameShape(QFrame.NoFrame)
        self.left_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                padding: 2px;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #ecf0f1;
                font-size: 11px;  /* Smaller font size */
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
            QListWidget:focus {
                border: 1px solid #3498db;
            }
        """)
        
        # Set alternating row colors
        self.left_list.setAlternatingRowColors(True)
        palette = self.left_list.palette()
        palette.setColor(QPalette.AlternateBase, QColor("#f9f9f9"))
        self.left_list.setPalette(palette)
        
        # Assemble left layout
        left_layout.addWidget(left_label)
        left_layout.addWidget(self.left_search_input)
        left_layout.addWidget(self.left_list)
        
        # Create right container
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add right title label
        right_label = QLabel(right_title)
        right_label.setStyleSheet(left_label.styleSheet())
        
        # Search input for right side
        self.right_search_input = QLineEdit()
        self.right_search_input.setPlaceholderText(f"Search {right_title.lower()}...")
        self.right_search_input.textChanged.connect(self.filter_right_items)
        self.right_search_input.setStyleSheet(self.left_search_input.styleSheet())
        
        # Create right list
        self.right_list = QListWidget()
        self.right_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.right_list.setFrameShape(QFrame.NoFrame)
        self.right_list.setStyleSheet(self.left_list.styleSheet())
        self.right_list.setPalette(palette)
        
        # Assemble right layout
        right_layout.addWidget(right_label)
        right_layout.addWidget(self.right_search_input)
        right_layout.addWidget(self.right_list)
        
        # Create button container with vertical layout
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Button style
        button_style = """
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                margin: 2px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """
        
        # Create transfer buttons
        self.move_all_right = QPushButton()
        self.move_all_right.setIcon(QIcon("icons/arrow_double_right.png"))
        
        self.move_right = QPushButton()
        self.move_right.setIcon(QIcon("icons/arrow_right.ico"))
        
        self.move_left = QPushButton()
        self.move_left.setIcon(QIcon("icons/arrow_left.ico"))
        
        self.move_all_left = QPushButton()
        self.move_all_left.setIcon(QIcon("icons/arrow_double_left.png"))
        
        # Set button styling
        for button in [self.move_all_right, self.move_right, self.move_left, self.move_all_left]:
            button.setStyleSheet(button_style)
        
        # Connect button signals
        self.move_all_right.clicked.connect(self.move_all_items_right)
        self.move_right.clicked.connect(self.move_selected_items_right)
        self.move_left.clicked.connect(self.move_selected_items_left)
        self.move_all_left.clicked.connect(self.move_all_items_left)
        
        # Create a container with precise button positioning
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to position buttons vertically centered with lists
        button_layout.addStretch(1)
        
        # Add buttons
        button_layout.addWidget(self.move_all_right)
        button_layout.addWidget(self.move_right)
        button_layout.addWidget(self.move_left)
        button_layout.addWidget(self.move_all_left)
        
        # Add stretch after buttons
        button_layout.addStretch(1)
        
        # Add containers to horizontal layout
        lists_layout.addWidget(left_container)
        lists_layout.addWidget(button_container)
        lists_layout.addWidget(right_container)
        
        # Add lists layout to main layout
        layout.addLayout(lists_layout)
    
    def filter_left_items(self, text):
        """Filter items in the left list based on search text"""
        for i in range(self.left_list.count()):
            item = self.left_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def filter_right_items(self, text):
        """Filter items in the right list based on search text"""
        for i in range(self.right_list.count()):
            item = self.right_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())
    
    def move_all_items_right(self):
        """Move all items from left list to right list."""
        while self.left_list.count() > 0:
            item = self.left_list.takeItem(0)
            self.right_list.addItem(item)
        self.items_transferred.emit()
            
    def move_selected_items_right(self):
        """Move selected items from left list to right list."""
        for item in self.left_list.selectedItems():
            self.right_list.addItem(self.left_list.takeItem(
                self.left_list.row(item)))
        self.items_transferred.emit()
            
    def move_selected_items_left(self):
        """Move selected items from right list to left list."""
        for item in self.right_list.selectedItems():
            self.left_list.addItem(self.right_list.takeItem(
                self.right_list.row(item)))
        self.items_transferred.emit()
            
    def move_all_items_left(self):
        """Move all items from right list to left list."""
        while self.right_list.count() > 0:
            item = self.right_list.takeItem(0)
            self.left_list.addItem(item)
        self.items_transferred.emit()
    
    def get_left_items(self):
        """Get all items from the left list, sorted."""
        return sorted(self.left_list.item(i).text() for i in range(self.left_list.count()))
    
    def get_right_items(self):
        """Get all items from the right list, sorted."""
        return sorted(self.right_list.item(i).text() for i in range(self.right_list.count()))
    
    def set_left_items(self, items):
        """Set items in the left list, sorted."""
        self.left_list.clear()
        # Convert to strings and sort
        sorted_items = sorted(str(item) for item in items)
        for item in sorted_items:
            self.left_list.addItem(item)
    
    def set_right_items(self, items):
        """Set items in the right list, sorted."""
        self.right_list.clear()
        # Convert to strings and sort
        sorted_items = sorted(str(item) for item in items)
        for item in sorted_items:
            self.right_list.addItem(item)

    def setFullHeight(self, full_height):
        if full_height:
            self.left_list.setMaximumHeight(16777215)  # Maximum possible value
            self.right_list.setMaximumHeight(16777215)
        else:
            self.left_list.setMaximumHeight(16777215 // 2)
            self.right_list.setMaximumHeight(16777215 // 2)



class DarkTwoListSelector(TwoListSelector):
    """
    A dark mode version of the TwoListSelector widget.
    Provides a modern dark look with consistent styling and item filtering.
    """

    def setup_ui(self, left_title, right_title):
        # Call the parent setup method to set up the basic structure
        super().setup_ui(left_title, right_title)

        # Disable alternating row colors to prevent white backgrounds
        self.left_list.setAlternatingRowColors(False)
        self.right_list.setAlternatingRowColors(False)

        # Dark mode color palette
        dark_styles = """
            QLabel {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 11px;  /* Smaller font size */
                padding: 3px;
                background-color: #3c3f41;
                border: 1px solid #5a5a5a;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            
            QLineEdit {
                background-color: #3c3f41;
                color: #e0e0e0;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 3px;
                font-size: 11px;  /* Smaller font size */
            }
            QLineEdit:focus {
                border: 1px solid #4a6984;
            }
            
            QListWidget {
                background-color: #3c3f41;
                color: #e0e0e0;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 2px;
            }
            QListWidget::item {
                background-color: #3c3f41;
                padding: 2px;
                border-bottom: 1px solid #4a4a4a;
                font-size: 11px;  /* Smaller font size */
            }
            QListWidget::item:selected {
                background-color: #4a6984;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #4a4a4a;
            }
            QListWidget:focus {
                border: 1px solid #4a6984;
            }
        """

        # Dark mode button style
        dark_button_style = """
            QPushButton {
                background-color: #4a6984;
                color: white;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 5px;
                margin: 2px;
                min-width: 30px;
            }
            QPushButton:hover {
                background-color: #5a7a9d;
            }
            QPushButton:pressed {
                background-color: #3a5a7d;
            }
        """

        # Apply dark styles to labels
        for label in [self.findChild(QLabel, left_title), self.findChild(QLabel, right_title)]:
            if label:
                label.setStyleSheet(dark_styles)

        # Apply dark styles to search inputs
        self.left_search_input.setStyleSheet(dark_styles)
        self.right_search_input.setStyleSheet(dark_styles)

        # Apply dark styles to lists
        self.left_list.setStyleSheet(dark_styles)
        self.right_list.setStyleSheet(dark_styles)

        # Apply dark styles to buttons
        for button in [self.move_all_right, self.move_right, self.move_left, self.move_all_left]:
            button.setStyleSheet(dark_button_style)

        # Set dark mode palette
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Base, QColor("#3c3f41"))  # Main background
        dark_palette.setColor(QPalette.AlternateBase, QColor("#3c3f41"))  # Fix bright white rows
        dark_palette.setColor(QPalette.Text, QColor("#e0e0e0"))  # Text color
        dark_palette.setColor(QPalette.WindowText, QColor("#e0e0e0"))

        # Apply the dark mode palette to both lists
        self.left_list.setPalette(dark_palette)
        self.right_list.setPalette(dark_palette)




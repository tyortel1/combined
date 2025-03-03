from PySide6.QtWidgets import QWidget, QLabel,QTextEdit, QComboBox, QLineEdit, QHBoxLayout, QDateTimeEdit
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator, QTextOption
from PySide6.QtCore import Signal





class StyledBaseWidget(QWidget):
    label_width = 120  # Default width
    
    @classmethod
    def calculate_label_width(cls, labels):
        """Calculate and set the width needed for the longest label"""
        test_label = QLabel()
        metrics = test_label.fontMetrics()
        max_width = 0
        for label in labels:
            width = metrics.horizontalAdvance(label)
            max_width = max(max_width, width)
        cls.label_width = max_width + 20  # Add padding for safety
        print(f"Set label width to: {cls.label_width}")  # Debug print
        return cls.label_width

    @classmethod
    def reset_label_width(cls):
        """Reset to default width if needed"""
        cls.label_width = 120

    def __init__(self, label_text, input_widget, parent=None):
        super().__init__(parent)
        self.setupUi(label_text, input_widget)
    
    def setupUi(self, label_text, input_widget):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Updated Label Style
        self.label = QLabel(label_text, self)
        self.label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-weight: 500;
                font-size: 13px;
                padding: 5px;
            }
        """)
        self.label.setFixedWidth(self.label_width)
    
        self.input_widget = input_widget
        self.input_widget.setFixedWidth(200)
    
        layout.addWidget(self.label)
        layout.addWidget(self.input_widget)
        layout.addStretch()
        layout.setAlignment(Qt.AlignLeft)

        self.selected_color_palette = []

class StyledDropdown(StyledBaseWidget):
    def __init__(self, label_text, items=None, editable=False, parent=None):
        print(label_text)
        self.combo = QComboBox()
        self.combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #000000;  /* Explicit black text */
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox:focus {
                border: 1px solid #3498db;
            }
            QComboBox QAbstractItemView {
                selection-background-color: #3498db;
                selection-color: #ffffff;  /* White text for selected items */
                background-color: #ffffff;
                color: #000000;  /* Explicit black text for dropdown items */
                border: 1px solid #bdc3c7;
            }

        """)
        
        if items:
            self.combo.addItems(items)
        self.combo.setEditable(bool(editable))  

        super().__init__(label_text, self.combo, parent)

    def setItems(self, items):
        """Set all items in the dropdown, clearing existing ones."""
        self.combo.clear()
        self.combo.addItems(items)

    def addItem(self, item):
        """Add a single item to the dropdown."""
        self.combo.addItem(item)

    def addItems(self, items):
        """Add multiple items to the dropdown."""
        self.combo.addItems(items)

    def currentText(self):
        """Get the current selected text."""
        return self.combo.currentText()

    def setCurrentText(self, text):
        """Set the current text."""
        self.combo.setCurrentText(text)

    def currentIndex(self):
        """Get the current selected index."""
        return self.combo.currentIndex()

    def setCurrentIndex(self, index):
        """Set the current index."""
        self.combo.setCurrentIndex(index)

    def clear(self):
        """Clear all items from the dropdown."""
        self.combo.clear()

    def count(self):
        """Get the number of items in the dropdown."""
        return self.combo.count()

    def itemText(self, index):
        """Get the text at the specified index."""
        return self.combo.itemText(index)

    def blockSignals(self, block):
        """Block or unblock signals from the combo box."""
        return self.combo.blockSignals(block)

    def currentIndexChanged(self):
        """Get the currentIndexChanged signal from the combo box."""
        return self.combo.currentIndexChanged


    def setItemData(self, index, value):
        """Set the data for the item at the given index."""
        self.combo.setItemData(index, value)

    def itemData(self, index):
        """Get the data associated with the item at the given index."""
        return self.combo.itemData(index)




        
class StyledInputBox(StyledBaseWidget):
    editingFinished = Signal()
    
    def __init__(self, label_text, default_value="", validator=None, parent=None):
        print(label_text)
        self.input_field = QLineEdit()
        self.input_field.setStyleSheet("""
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
        self.input_field.setText(str(default_value))
        # Remove the minimum width setting - let base widget handle it
        
        if validator:
            self.input_field.setValidator(validator)
            
        super().__init__(label_text, self.input_field, parent)
        self.input_field.editingFinished.connect(self.editingFinished.emit)
    def text(self):
        return self.input_field.text()

    def setText(self, text):
        self.input_field.setText(text)






class StyledDateSelector(StyledBaseWidget):
    def __init__(self, label_text, default_date=None, parent=None):
        self.date_edit = QDateTimeEdit()
        self.date_edit.setCalendarPopup(True)  # Enables calendar popup
        
        # Set default date if provided, otherwise use current date
        if default_date:
            self.date_edit.setDate(default_date)
        else:
            self.date_edit.setDate(QDate.currentDate())

        self.date_edit.setStyleSheet("""
            QDateTimeEdit {
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
            }
            QDateTimeEdit:focus {
                border: 1px solid #3498db;
            }
        """)

        super().__init__(label_text, self.date_edit, parent)

    def date(self):
        """ Returns the selected date as a QDate object """
        return self.date_edit.date()

    def setDate(self, date):
        """ Sets the date in the date picker """
        self.date_edit.setDate(date)

    def dateString(self, format=Qt.ISODate):
        """ Returns the selected date as a string """
        return self.date_edit.date().toString(format)




# Dark Mode Components
class DarkStyledBaseWidget(StyledBaseWidget):
    # Dark theme colors
    DARK_BG = "#1e1e1e"
    DARK_WIDGET_BG = "#2d2d2d"
    DARK_BORDER = "#3d3d3d"
    DARK_TEXT = "#ffffff"  # White text for dark mode
    DARK_ACCENT = "#0f84d8"
    DARK_DISABLED = "#404040"

    def setupUi(self, label_text, input_widget):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Updated Label Style
        self.label = QLabel(label_text, self)
        self.label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: 500;
                font-size: 13px;
                padding: 5px;
                background: transparent;
            }
        """)
        self.label.setFixedWidth(self.label_width)

        self.input_widget = input_widget
        self.input_widget.setFixedWidth(200)

        layout.addWidget(self.label)
        layout.addWidget(self.input_widget)
        layout.addStretch()
        layout.setAlignment(Qt.AlignLeft)

class DarkStyledDropdown(StyledDropdown):
    def __init__(self, label_text, items=None, editable=False, parent=None):
        super().__init__(label_text, items, editable, parent)
        
        # Explicitly set label color to white
        self.label.setStyleSheet("""
            QLabel {
                color: white !important;
                background: transparent;
                border: none;
            }
        """)
        
        # Additional styling for the dropdown
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
                border: 1px solid {DarkStyledBaseWidget.DARK_BORDER};
                border-radius: 4px;
                padding: 5px;
            }}
            QComboBox:focus {{
                border: 1px solid {DarkStyledBaseWidget.DARK_ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                background: {DarkStyledBaseWidget.DARK_WIDGET_BG};
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {DarkStyledBaseWidget.DARK_TEXT};
                margin-right: 5px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
                selection-background-color: {DarkStyledBaseWidget.DARK_ACCENT};
                selection-color: {DarkStyledBaseWidget.DARK_TEXT};
                border: 1px solid {DarkStyledBaseWidget.DARK_BORDER};
            }}
            QComboBox:disabled {{
                background-color: {DarkStyledBaseWidget.DARK_DISABLED};
                color: #808080;
            }}
        """)

class DarkStyledInputBox(StyledInputBox):
    def __init__(self, label_text, default_value="", validator=None, parent=None):
        super().__init__(label_text, default_value, validator, parent)
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
                border: 1px solid {DarkStyledBaseWidget.DARK_BORDER};
                border-radius: 4px;
                padding: 5px;
            }}
            QLineEdit:focus {{
                border: 1px solid {DarkStyledBaseWidget.DARK_ACCENT};
            }}
            QLineEdit:disabled {{
                background-color: {DarkStyledBaseWidget.DARK_DISABLED};
                color: #808080;
            }}
        """)

class DarkStyledDateSelector(StyledDateSelector):
    def __init__(self, label_text, default_date=None, parent=None):
        super().__init__(label_text, default_date, parent)
        self.date_edit.setStyleSheet(f"""
            QDateTimeEdit {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
                border: 1px solid {DarkStyledBaseWidget.DARK_BORDER};
                border-radius: 4px;
                padding: 5px;
            }}
            QDateTimeEdit:focus {{
                border: 1px solid {DarkStyledBaseWidget.DARK_ACCENT};
            }}
            QDateTimeEdit::up-button, QDateTimeEdit::down-button {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                border: none;
            }}
            QDateTimeEdit::up-arrow {{
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 5px solid {DarkStyledBaseWidget.DARK_TEXT};
            }}
            QDateTimeEdit::down-arrow {{
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {DarkStyledBaseWidget.DARK_TEXT};
            }}
            QCalendarWidget {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
            }}
            QCalendarWidget QToolButton {{
                color: {DarkStyledBaseWidget.DARK_TEXT};
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
            }}
            QCalendarWidget QMenu {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
            }}
            QCalendarWidget QSpinBox {{
                background-color: {DarkStyledBaseWidget.DARK_WIDGET_BG};
                color: {DarkStyledBaseWidget.DARK_TEXT};
            }}
        """)

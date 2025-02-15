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

        # Common Label
        self.label = QLabel(label_text, self)
        self.label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-weight: bold;
                font-size: 12px;
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
                background-color: white;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox:focus {
                border: 1px solid #3498db;
            }
        """)
        
        if items:
            self.combo.addItems(items)
        self.combo.setEditable(bool(editable))  

        super().__init__(label_text, self.combo, parent)

    def setItems(self, items):
        self.combo.clear()
        self.combo.addItems(items)

    def currentText(self):
        return self.combo.currentText()

    def setCurrentText(self, text):
        self.combo.setCurrentText(text)

    def currentIndex(self):
        return self.combo.currentIndex()

    def setCurrentIndex(self, index):
        self.combo.setCurrentIndex(index)

    def clear(self):
        self.combo.clear()



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
        self.input_field.setMinimumWidth(250)  # Ensure it’s wide enough

        if validator:
            self.input_field.setValidator(validator)

        super().__init__(label_text, self.input_field, parent)

        # ✅ Read the updated label width from `StyledBaseWidget.label_width`
        updated_width = StyledBaseWidget.label_width  
        print(f"StyledInputBox applying label width: {updated_width}")  # Debugging print
        self.label.setFixedWidth(updated_width)  # ✅ Apply the correct width

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


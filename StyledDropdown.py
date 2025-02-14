from PySide6.QtWidgets import QWidget, QLabel, QComboBox, QLineEdit, QHBoxLayout, QDateTimeEdit
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Signal


class StyledBaseWidget(QWidget):
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
        self.label.setFixedWidth(120)  # Fixed width for consistency
        
        self.input_widget = input_widget
        self.input_widget.setFixedWidth(200)  # Fixed width to match all widgets
        
        layout.addWidget(self.label)
        layout.addWidget(self.input_widget)
        layout.addStretch()  # Aligns nicely with other widgets
        layout.setAlignment(Qt.AlignLeft)

        self.selected_color_palette = []

class StyledDropdown(StyledBaseWidget):
    def __init__(self, label_text, items=None, editable=False, parent=None):
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
    editingFinished = Signal()  # Add this Signal before __init__

    def __init__(self, label_text, default_value="", validator=None, parent=None):
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


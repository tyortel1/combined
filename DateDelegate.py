from PyQt5.QtWidgets import QStyledItemDelegate, QDateTimeEdit
from PyQt5.QtCore import QDateTime, Qt

class DateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        try:
            editor = QDateTimeEdit(parent)
            editor.setDisplayFormat("yyyy-MM-dd")
            editor.setCalendarPopup(True)
            return editor
        except Exception as e:
            print(f"Error in createEditor: {e}")
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        try:
            date_str = index.model().data(index, Qt.EditRole)
            if date_str:
                date = QDateTime.fromString(date_str, "yyyy-MM-dd")
                if date.isValid():
                    editor.setDateTime(date)
                else:
                    print(f"Invalid date format: {date_str}. Setting current date.")
                    editor.setDateTime(QDateTime.currentDateTime())
            else:
                print("No date string found. Setting current date.")
                editor.setDateTime(QDateTime.currentDateTime())
        except Exception as e:
            print(f"Error in setEditorData: {e}")

    def setModelData(self, editor, model, index):
        try:
            editor.interpretText()
            date = editor.dateTime()
            date_str = date.toString("yyyy-MM-dd")
            print(f"Setting model data: {date_str}")
        
            # Validate date before setting
            if date.isValid():
                model.setData(index, date_str, Qt.EditRole)
                print(f"Model data set successfully: {date_str}")
            else:
                print(f"Invalid date encountered: {date_str}")
        except Exception as e:
            print(f"Error in setModelData: {e}")

    def updateEditorGeometry(self, editor, option, index):
        try:
            editor.setGeometry(option.rect)
        except Exception as e:
            print(f"Error in updateEditorGeometry: {e}")

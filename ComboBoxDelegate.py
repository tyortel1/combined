from PySide6.QtWidgets import QComboBox, QItemDelegate

class ComboBoxDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.decline_curve_names = []  # Initialize with an empty list

    def setDeclineCurveNames(self, names):
        self.decline_curve_names = names

    def createEditor(self, parent, option, index):
        # Create a QComboBox editor when editing a cell in the "Decline Curve" column
        editor = QComboBox(parent)
        editor.addItems(self.decline_curve_names)  # Populate with names
        return editor

    def setEditorData(self, editor, index):
        # Set the data to be displayed and the current item in the QComboBox
        item_text = index.data()
        editor.setCurrentText(item_text)

    def setModelData(self, editor, model, index):
        # Get the current text from the QComboBox and set it in the model
        model.setData(index, editor.currentText())

    def updateEditorGeometry(self, editor, option, index):
        # Update the geometry of the editor when displayed in the table
        editor.setGeometry(option.rect)
